from typing import Optional

from shell_tests.configs import (
    CloudShellConfig,
    DeploymentResourceConfig,
    MainConfig,
    SandboxConfig,
)
from shell_tests.errors import BaseAutomationException, CSIsNotAliveError
from shell_tests.handlers.cs_handler import CloudShellHandler
from shell_tests.handlers.resource_handler import DeploymentResourceHandler
from shell_tests.handlers.sandbox_handler import SandboxHandler
from shell_tests.helpers.logger import logger


class CSCreator:
    def __init__(self, conf: MainConfig):
        self.conf = conf
        self.do_handler = CloudShellHandler(self.conf.do_conf)
        self._do_sandbox_handler: Optional[SandboxHandler] = None

    def _find_topology_name_for_cloudshell(self) -> str:
        cs_names = sorted(self.do_handler.get_topologies_by_category("CloudShell"))
        for topology_name in cs_names:
            # 'Environments/CloudShell - Latest 8.3'
            if topology_name.split("/", 1)[-1] == self.conf.do_conf.cs_version:
                return topology_name
        raise BaseAutomationException(
            f"CloudShell version {self.conf.do_conf.cs_version} isn't exists"
        )

    def _start_cs_sandbox(self) -> SandboxHandler:
        topology_name = self._find_topology_name_for_cloudshell()
        logger.debug(f"Creating CloudShell {topology_name}")
        conf = SandboxConfig(
            **{
                "Name": "auto tests",
                "Resources": [],
                "Blueprint Name": topology_name,
                "Specific Version": self.conf.do_conf.cs_specific_version,
            }
        )
        return SandboxHandler.create(conf, self.do_handler)

    def _get_cs_resource(
        self, sandbox_handler: SandboxHandler
    ) -> DeploymentResourceHandler:
        cs_deployed_resource_conf = DeploymentResourceConfig(
            **{"Name": "CloudShell", "Blueprint Name": self.conf.do_conf.cs_version}
        )
        return DeploymentResourceHandler.create_from_conf(
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
                self.conf.cs_conf = conf
                return cs_handler
        else:
            raise CSIsNotAliveError("All 5 CloudShells are not started")

    def finish(self):
        if self._do_sandbox_handler is not None:
            logger.info("Deleting CS on Do")
            self._do_sandbox_handler.end_reservation()
