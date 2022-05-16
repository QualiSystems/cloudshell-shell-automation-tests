from collections.abc import Iterable
from concurrent import futures as ft
from typing import Optional

from retrying import retry

from shell_tests.configs import (
    CloudShellConfig,
    CSonDoConfig,
    DeploymentResourceConfig,
    MainConfig,
    NetworkingAppConf,
    SandboxConfig,
)
from shell_tests.errors import BaseAutomationException, CSIsNotAliveError
from shell_tests.handlers.cs_handler import CloudShellHandler
from shell_tests.handlers.resource_handler import DeploymentResourceHandler
from shell_tests.handlers.sandbox_handler import SandboxHandler
from shell_tests.helpers.logger import logger
from shell_tests.helpers.threads_helper import set_thread_name_with_suffix


class DoHandler:
    def __init__(self, conf: MainConfig):
        self._conf = conf
        self._do_handler = CloudShellHandler(conf.do_conf)
        self._cs_creator = CSCreator(self._do_handler, conf.do_conf.cs_on_do_conf)
        self._networking_apps_handler = NetworkingAppsHandler(
            self._do_handler, conf.do_conf.networking_apps
        )

    def _prepare(self):
        with ft.ThreadPoolExecutor(
            5, thread_name_prefix="[Do-reservation]"
        ) as executor:
            cs_future = None
            if self._conf.do_conf.cs_on_do_conf is not None:
                cs_future = self._cs_creator.create_cloudshell(executor)
            app_futures = self._networking_apps_handler.create_apps(executor)

            for future in ft.as_completed(app_futures):
                handler: DeploymentResourceHandler = future.result()
                self._update_resource_conf_from_deployment_resource(handler)
            if cs_future is not None:
                cs_conf = cs_future.result()
                self._conf.cs_conf = cs_conf

    def prepare(self):
        try:
            self._prepare()
        except Exception:
            self.finish()
            raise

    def finish(self):
        if self._conf.do_conf.cs_on_do_conf is not None:
            if self._conf.do_conf.cs_on_do_conf.delete_cs:
                self._cs_creator.finish()
            else:
                ip = self._conf.cs_conf.host
                msg = f"The CS is not deleted, you can still use it - http://{ip}"
                logger.info(msg)
        self._networking_apps_handler.finish()

    def _update_resource_conf_from_deployment_resource(
        self, handler: DeploymentResourceHandler
    ):
        try:
            conf = next(
                c
                for c in self._conf.resources_conf
                if c.networking_app_name == handler.conf.name
            )
        except StopIteration:
            emsg = f"Resource {handler.conf.name} is not present in resources config"
            raise BaseAutomationException(emsg)
        conf.device_ip = handler.device_ip
        if not conf.attributes.get("User"):
            attrs = {
                "User": "admin",
                "Password": "admin",
                "Enable Password": "admin",
            }
            conf.attributes.update(attrs)

    def __enter__(self):
        self.prepare()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finish()
        return False


class CSCreator:
    def __init__(self, do_handler: CloudShellHandler, cs_on_do_conf: CSonDoConfig):
        self._do_handler = do_handler
        self._cs_on_do_conf = cs_on_do_conf
        self._cs_on_do_sandbox_handler: Optional[SandboxHandler] = None

    def _find_topology_name_for_cloudshell(self) -> str:
        cs_names = sorted(self._do_handler.get_topologies_by_category(""))
        for topology_name in cs_names:
            # 'Environments/CloudShell - Latest 8.3'
            if topology_name.split("/", 1)[-1] == self._cs_on_do_conf.cs_version:
                return topology_name
        emsg = f"CloudShell version {self._cs_on_do_conf.cs_version} isn't exists"
        raise BaseAutomationException(emsg)

    def _start_cs_sandbox(self) -> SandboxHandler:
        topology_name = self._find_topology_name_for_cloudshell()
        logger.debug(f"Creating CloudShell {topology_name}")
        conf = SandboxConfig(
            **{
                "Name": topology_name,
                "Resources": [],
                "Blueprint Name": topology_name,
                "Specific Version": self._cs_on_do_conf.cs_specific_version,
            }
        )
        return SandboxHandler.create(conf, self._do_handler)

    def _get_cs_resource(
        self, sandbox_handler: SandboxHandler
    ) -> DeploymentResourceHandler:
        conf = DeploymentResourceConfig(
            **{"Name": "CloudShell", "Blueprint Name": self._cs_on_do_conf.cs_version}
        )
        return DeploymentResourceHandler.create_resource(conf, sandbox_handler)

    def _get_cs_config(self, sandbox_handler: SandboxHandler) -> CloudShellConfig:
        resource = self._get_cs_resource(sandbox_handler)
        info = resource.get_details()
        attrs = {attr.Name: attr.Value for attr in info.ResourceAttributes}
        data = {
            "Host": info.Address,
            "User": "admin",
            "Password": "admin",
            "OS User": attrs["OS Login"],
            "OS Password": attrs["OS Password"],
        }
        logger.info(f"CloudShell created IP: http://{info.Address}")
        return CloudShellConfig(**data)

    @retry(
        stop_max_attempt_number=5,
        retry_on_exception=lambda e: isinstance(e, CSIsNotAliveError),
    )
    def _create_cloudshell(self) -> CloudShellConfig:
        set_thread_name_with_suffix("CloudShell")
        self._cs_on_do_sandbox_handler = self._start_cs_sandbox()
        try:
            conf = self._get_cs_config(self._cs_on_do_sandbox_handler)
            cs_handler = CloudShellHandler(conf)
            cs_handler.wait_for_cs_is_started()
        except CSIsNotAliveError:
            self.finish()
            raise
        except Exception as e:
            logger.exception(f"The CS is not started {e}")
            raise e
        else:
            return conf

    def create_cloudshell(self, executor: ft.ThreadPoolExecutor) -> ft.Future:
        return executor.submit(self._create_cloudshell)

    def finish(self):
        if self._cs_on_do_sandbox_handler is not None:
            logger.info("Deleting CS on Do")
            self._cs_on_do_sandbox_handler.end_reservation(wait=False)


class NetworkingAppsHandler:
    def __init__(
        self,
        do_handler: CloudShellHandler,
        networking_app_configs: Iterable[NetworkingAppConf],
    ):
        self._do_handler = do_handler
        self._networking_app_configs = networking_app_configs
        self._sandbox_handlers: set[SandboxHandler] = set()

    def _create_app(self, app_conf: NetworkingAppConf) -> DeploymentResourceHandler:
        set_thread_name_with_suffix(f"Networking-App-{app_conf.name}")
        sandbox_handler = self._start_app_sandbox(app_conf.blueprint_name)
        self._sandbox_handlers.add(sandbox_handler)
        return self._get_app_resource(sandbox_handler, app_conf)

    def create_apps(self, executor: ft.ThreadPoolExecutor) -> set[ft.Future]:
        return {
            executor.submit(self._create_app, app_conf)
            for app_conf in self._networking_app_configs
        }

    @staticmethod
    def _get_app_resource(
        sandbox_handler: SandboxHandler, app_conf: NetworkingAppConf
    ) -> DeploymentResourceHandler:
        conf = DeploymentResourceConfig(
            **{"Name": app_conf.name, "Blueprint Name": app_conf.blueprint_name}
        )
        return DeploymentResourceHandler.create_resource(conf, sandbox_handler)

    def _find_topology_name_for_app(self, app_name: str) -> str:
        names = sorted(self._do_handler.get_topologies_by_category("Networking Apps"))
        for topology_name in names:
            # 'Environments/Cisco IOSv Switch'
            if topology_name.split("/", 1)[-1] == app_name:
                return topology_name
        raise BaseAutomationException(f"Networking App {app_name} isn't exists")

    def _start_app_sandbox(self, app_name: str) -> SandboxHandler:
        topology_name = self._find_topology_name_for_app(app_name)
        logger.debug(f"Creating Networking App {topology_name}")
        conf = SandboxConfig(
            **{
                "Name": f"Networking App {app_name}",
                "Resources": [],
                "Blueprint Name": topology_name,
            }
        )
        return SandboxHandler.create(conf, self._do_handler)

    def finish(self):
        if self._sandbox_handlers:
            logger.info("Stopping Networking Apps on Do")
            for sandbox_handler in self._sandbox_handlers:
                sandbox_handler.end_reservation(wait=False)
