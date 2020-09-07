from typing import List, Optional

from shell_tests.configs import (
    CloudShellConfig,
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


class CSCreator:
    def __init__(self, conf: MainConfig):
        self._conf = conf
        self._do_handler = CloudShellHandler(self._conf.do_conf)
        self._do_sandbox_handler: Optional[SandboxHandler] = None
        self._networking_apps_handler = NetworkingAppsHandler(self._do_handler, conf)

    def _find_topology_name_for_cloudshell(self) -> str:
        cs_names = sorted(self._do_handler.get_topologies_by_category(""))
        for topology_name in cs_names:
            # 'Environments/CloudShell - Latest 8.3'
            if topology_name.split("/", 1)[-1] == self._conf.do_conf.cs_version:
                return topology_name
        emsg = f"CloudShell version {self._conf.do_conf.cs_version} isn't exists"
        raise BaseAutomationException(emsg)

    def _start_cs_sandbox(self) -> SandboxHandler:
        topology_name = self._find_topology_name_for_cloudshell()
        logger.debug(f"Creating CloudShell {topology_name}")
        conf = SandboxConfig(
            **{
                "Name": "auto tests",
                "Resources": [],
                "Blueprint Name": topology_name,
                "Specific Version": self._conf.do_conf.cs_specific_version,
            }
        )
        return SandboxHandler.create(conf, self._do_handler)

    def _get_cs_resource(
        self, sandbox_handler: SandboxHandler
    ) -> DeploymentResourceHandler:
        cs_deployed_resource_conf = DeploymentResourceConfig(
            **{"Name": "CloudShell", "Blueprint Name": self._conf.do_conf.cs_version}
        )
        return DeploymentResourceHandler.create_resource(
            cs_deployed_resource_conf, sandbox_handler
        )

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
        logger.info(f"CloudShell created IP: {info.Address}")
        return CloudShellConfig(**data)

    def create_cloudshell(self) -> CloudShellHandler:
        for _ in range(5):
            self._do_sandbox_handler = self._start_cs_sandbox()
            try:
                conf = self._get_cs_config(self._do_sandbox_handler)
                cs_handler = CloudShellHandler(conf)
                cs_handler.wait_for_cs_is_started()
            except CSIsNotAliveError:
                logger.exception("The CS is not started")
                self.finish()
            except Exception as e:
                self.finish()
                raise e
            else:
                self._conf.cs_conf = conf
                break
        else:
            raise CSIsNotAliveError("All 5 CloudShells are not started")

        try:
            self._networking_apps_handler.create_apps()
        except BaseException:
            self.finish()
            raise

        return cs_handler

    def finish(self):
        self._networking_apps_handler.finish()
        if self._do_sandbox_handler is not None:
            logger.info("Deleting CS on Do")
            self._do_sandbox_handler.end_reservation()


class NetworkingAppsHandler:
    def __init__(self, do_handler: CloudShellHandler, conf: MainConfig):
        self._conf = conf
        self._do_handler = do_handler
        self._sandbox_handlers: List[SandboxHandler] = []
        self._deployment_resource_handlers: List[DeploymentResourceHandler] = []

    def create_apps(self):
        try:
            for app_conf in self._conf.do_conf.networking_apps:
                sandbox_handler = self._start_app_sandbox(app_conf.blueprint_name)
                self._sandbox_handlers.append(sandbox_handler)
                deployment_resource_handler = self._get_app_resource(
                    sandbox_handler, app_conf
                )
                self._deployment_resource_handlers.append(deployment_resource_handler)
                self._update_resource_conf_from_deployment_resource(
                    deployment_resource_handler
                )
        except BaseException:
            self.finish()
            raise

    def _update_resource_conf_from_deployment_resource(
        self, deployment_resource_handler: DeploymentResourceHandler
    ):
        for r_conf in self._conf.resources_conf:
            if r_conf.networking_app_name == deployment_resource_handler.conf.name:
                r_conf.device_ip = deployment_resource_handler.device_ip
                if not r_conf.attributes.get("User"):
                    attrs = {
                        "User": "admin",
                        "Password": "admin",
                        "Enable Password": "admin",
                    }
                    r_conf.attributes.update(attrs)

    @staticmethod
    def _get_app_resource(
        sandbox_handler: SandboxHandler, app_conf: NetworkingAppConf
    ) -> DeploymentResourceHandler:
        deployment_resource_conf = DeploymentResourceConfig(
            **{"Name": app_conf.name, "Blueprint Name": app_conf.blueprint_name}
        )
        return DeploymentResourceHandler.create_resource(
            deployment_resource_conf, sandbox_handler
        )

    def _find_topology_name_for_app(self, app_name: str) -> str:
        names = sorted(self._do_handler.get_topologies_by_category("Networking Apps"))
        for topology_name in names:
            # 'Environments/Cisco IOSv Switch'
            if topology_name.split("/", 1)[-1] == app_name:
                return topology_name
        raise BaseAutomationException(f"Networking App {app_name} isn't exists")

    def _start_app_sandbox(self, app_name) -> SandboxHandler:
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
        logger.info("Stopping Networking Apps on Do")
        for sandbox_handler in self._sandbox_handlers:
            sandbox_handler.end_reservation()
