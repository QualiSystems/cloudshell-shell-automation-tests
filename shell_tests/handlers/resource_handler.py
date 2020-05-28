from enum import Enum
from functools import cached_property
from typing import Dict, List, Optional

from cloudshell.api.cloudshell_api import ResourceInfo
from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.configs import (
    DeploymentResourceConfig,
    ResourceConfig,
    ServiceConfig,
    TestsConfig,
)
from shell_tests.errors import BaseAutomationException
from shell_tests.handlers.cs_handler import CloudShellHandler
from shell_tests.handlers.sandbox_handler import SandboxHandler
from shell_tests.handlers.shell_handler import ShellHandler
from shell_tests.helpers.logger import logger


class DeviceType(Enum):
    REAL_DEVICE = "Real device"
    SIMULATOR = "Simulator"
    WITHOUT_DEVICE = "Without device"


class ResourceHandler:
    def __init__(
        self,
        conf: ResourceConfig,
        cs_handler: CloudShellHandler,
        shell_handler: ShellHandler,
    ):
        self.conf = conf
        self.name = conf.name
        self.attributes = {}
        self.children_attributes = conf.children_attributes
        self._cs_handler = cs_handler
        self._shell_handler = shell_handler

        self.is_autoload_finished = False
        self._sandbox_handler = None

    @classmethod
    def create(
        cls,
        conf: ResourceConfig,
        cs_handler: CloudShellHandler,
        shell_handler: ShellHandler,
    ) -> "ResourceHandler":
        logger.info(f"Start preparing the resource {conf.name}")
        resource = cls(conf, cs_handler, shell_handler,)
        resource._create_resource()
        logger.info(f"The resource {resource.name} prepared")
        return resource

    @property
    def sandbox_handler(self) -> SandboxHandler:
        if self._sandbox_handler is None:
            raise BaseAutomationException("You have to add Sandbox Handler")
        return self._sandbox_handler

    @sandbox_handler.setter
    def sandbox_handler(self, val: SandboxHandler):
        self._sandbox_handler = val

    @cached_property
    def family(self) -> str:
        return self.get_details().ResourceFamilyName

    @property
    def device_type(self) -> DeviceType:
        if not self.conf.device_ip:
            return DeviceType.WITHOUT_DEVICE
        elif self.conf.attributes.get("User"):
            return DeviceType.REAL_DEVICE
        else:
            return DeviceType.SIMULATOR

    @property
    def model(self) -> str:
        return self._shell_handler.model

    def _create_resource(self):
        ip = self.conf.device_ip or "127.0.0.1"  # if we don't have a real device
        self.name = self._cs_handler.create_resource(self.name, self.model, ip)
        if self.conf.attributes:
            self.set_attributes(self.conf.attributes)

    def set_attributes(self, attributes: Dict[str, str]):
        """Set attributes for the resource and update internal dict."""
        namespace = self.model if not self.conf.is_first_gen else ""
        self._cs_handler.set_resource_attributes(self.name, namespace, attributes)
        self.attributes.update(attributes)

    def set_children_attributes(self, children_attributes: Dict[str, Dict[str, str]]):
        """Set children attributes."""
        for child_name, attributes in children_attributes.items():
            child_name = f"{self.name}/{child_name}"
            child_info = self._cs_handler.get_resource_details(child_name)

            for attribute_name, attribute_value in attributes.items():
                self._set_child_attribute(child_info, attribute_name, attribute_value)

    def _set_child_attribute(
        self, child_info: ResourceInfo, attribute_name: str, attribute_value: str,
    ):
        namespace = child_info.ResourceModelName
        for attribute_info in child_info.ResourceAttributes:
            namespace, name = attribute_info.Name.rsplit(".", 1)
            if name == attribute_name:
                break
        self._cs_handler.set_resource_attributes(
            child_info.Name, namespace, {attribute_name: attribute_value}
        )

    def autoload(self):
        """Run Autoload for the resource."""
        try:
            self._cs_handler.resource_autoload(self.name)
        except CloudShellAPIError as e:
            if str(e.code) != "129" and e.message != "no driver associated":
                raise
            self._cs_handler.update_driver_for_the_resource(self.name, self.model)
            self._cs_handler.resource_autoload(self.name)

        self.is_autoload_finished = True
        if self.children_attributes:
            self.set_children_attributes(self.children_attributes)

    def get_details(self) -> ResourceInfo:
        """Get resource details."""
        return self._cs_handler.get_resource_details(self.name)

    def get_commands(self) -> List[str]:
        return self._cs_handler.get_resource_commands(self.name)

    def execute_command(self, command_name: str, command_kwargs: Dict[str, str]) -> str:
        """Execute the command for the resource."""
        return self.sandbox_handler.execute_resource_command(
            self.name, command_name, command_kwargs
        )

    def health_check(self) -> str:
        """Run health check command on the resource."""
        logger.info(f'Starting a "health_check" command for the {self.name}')
        output = self.execute_command("health_check", {})
        logger.debug(f"Health check output: {output}")
        return output

    def run_custom_command(self, command: str) -> str:
        """Execute run custom command on the resource."""
        logger.info(f'Start a "run_custom_command" command {command}')
        output = self.execute_command("run_custom_command", {"custom_command": command})
        logger.debug(f"Run custom command output: {output}")
        return output

    def run_custom_config_command(self, command: str) -> str:
        """Execute run custom config command on the resource."""
        logger.info(f'Start a "run_custom_config_command" command {command}')
        output = self.execute_command(
            "run_custom_config_command", {"custom_command": command}
        )
        logger.debug(f"Run custom config command output: {output}")
        return output

    def save(self, path_to_save: str, configuration_type: str) -> str:
        """Execute save command on the resource."""
        logger.info('Start a "save" command')
        logger.debug(
            f"Path to save: {path_to_save}, configuration type: {configuration_type}"
        )

        output = self.execute_command(
            "save",
            {"folder_path": path_to_save, "configuration_type": configuration_type},
        )
        logger.debug(f"Save command output: {output}")
        return output

    def orchestration_save(self, mode: str, custom_params: str = "") -> str:
        """Execute orchestration save command."""
        logger.info('Start a "orchestration save" command')
        logger.debug(f"Mode: {mode}, custom params: {custom_params}")
        output = self.execute_command(
            "orchestration_save", {"mode": mode, "custom_params": custom_params},
        )
        logger.debug(f"Orchestration save command output: {output}")
        return output

    def restore(self, path: str, configuration_type: str, restore_method: str) -> str:
        """Execute restore command.

        :param path: path to the file
        :param configuration_type: startup or running
        :param restore_method: append or override
        """
        logger.info('Start a "restore" command')
        logger.debug(
            f"Path: {path}, configuration_type: {configuration_type}, "
            f"restore_method: {restore_method}"
        )
        output = self.execute_command(
            "restore",
            {
                "path": path,
                "configuration_type": configuration_type,
                "restore_method": restore_method,
            },
        )
        logger.debug(f"Restore command output: {output}")
        return output

    def orchestration_restore(
        self, saved_artifact_info: str, custom_params: str = ""
    ) -> str:
        """Execute orchestration restore command."""
        logger.info('Start a "orchestration restore" command')
        logger.debug(
            f"Saved artifact: {saved_artifact_info}, custom params: {custom_params}"
        )
        output = self.execute_command(
            "orchestration_restore",
            {
                "saved_artifact_info": saved_artifact_info,
                "custom_params": custom_params,
            },
        )
        logger.debug(f"Orchestration restore command output: {output}")
        return output

    def rename(self, new_name: str):
        """Rename the resource."""
        self.name = self._cs_handler.rename_resource(self.name, new_name)

    def finish(self):
        self._cs_handler.delete_resource(self.name)


class ServiceHandler:
    def __init__(
        self, name: str, attributes: Dict[str, str], model: str,
    ):
        self.name = name
        self.model = model
        self.family = None
        self.attributes = attributes

        self._sandbox_handler = None

    @classmethod
    def from_conf(cls, conf: ServiceConfig) -> "ServiceHandler":
        return cls(conf.name, conf.attributes, conf.model,)

    @property
    def sandbox_handler(self) -> SandboxHandler:
        if self._sandbox_handler is None:
            raise BaseAutomationException("You have to add Sandbox Handler")
        return self._sandbox_handler

    @sandbox_handler.setter
    def sandbox_handler(self, val: SandboxHandler):
        self._sandbox_handler = val

    @property
    def device_type(self) -> DeviceType:
        return DeviceType.REAL_DEVICE

    def execute_command(self, command_name: str, command_kwargs: Dict[str, str]) -> str:
        """Execute the command for the service."""
        return self.sandbox_handler.execute_service_command(
            self.name, command_name, command_kwargs
        )

    def load_config(self, config_path: str, extra_kwargs: Optional[Dict] = None) -> str:
        """Execute a command load_config for the service."""
        extra_kwargs = extra_kwargs or {}
        extra_kwargs.update({"config_file_location": config_path})
        return self.execute_command("load_config", extra_kwargs)

    def start_traffic(self, extra_kwargs: Optional[Dict] = None) -> str:
        """Execute a command start traffic for the service."""
        return self.execute_command("start_traffic", extra_kwargs or {})

    def stop_traffic(self, extra_kwargs: Optional[Dict] = None) -> str:
        """Execute a command stop traffic for the service."""
        return self.execute_command("stop_traffic", extra_kwargs or {})

    def get_statistics(self, extra_kwargs: Optional[Dict] = None) -> str:
        """Execute a command get statistics for the service."""
        return self.execute_command("get_statistics", extra_kwargs or {})

    def get_test_file(self, test_name: str) -> str:
        """Execute a command get test file for the service."""
        return self.execute_command("get_test_file", {"test_name": test_name})


class DeploymentResourceHandler:
    def __init__(
        self,
        name: str,
        is_first_gen: bool,
        attributes: Dict[str, str],
        children_attributes: Dict[str, Dict[str, str]],
        vm_name: str,
        sandbox_handler: SandboxHandler,
    ):
        self.name = name
        self.is_first_gen = is_first_gen
        self.attributes = attributes
        self.children_attributes = children_attributes
        self.vm_name = vm_name
        self.sandbox_handler = sandbox_handler
        self._cs_handler = sandbox_handler._cs_handler

    @classmethod
    def create_resource(
        cls,
        name: str,
        is_first_gen: bool,
        attributes: Dict[str, str],
        children_attributes: Dict[str, Dict[str, str]],
        blueprint_name: str,
        sandbox_handler: SandboxHandler,
    ) -> "DeploymentResourceHandler":
        logger.info(f"Start preparing the resource {name}")
        vm_name = name = sandbox_handler.get_deployment_resource_name(blueprint_name)
        resource = cls(
            name,
            is_first_gen,
            attributes,
            children_attributes,
            vm_name,
            sandbox_handler,
        )
        if attributes:
            resource.set_attributes(attributes)
        logger.info(f"The resource {resource.name} prepared")
        return resource

    @classmethod
    def create_from_conf(
        cls, conf: DeploymentResourceConfig, sandbox_handler: SandboxHandler,
    ) -> "DeploymentResourceHandler":
        return cls.create_resource(
            conf.name,
            conf.is_first_gen,
            conf.attributes,
            conf.children_attributes,
            conf.blueprint_name,
            sandbox_handler,
        )

    @property
    def device_type(self):
        return DeviceType.REAL_DEVICE

    @cached_property
    def model(self):
        return self.get_details().ResourceModelName

    @cached_property
    def device_ip(self):
        return self.get_details().Address

    def rename(self, new_name: str):
        self.name = self._cs_handler.rename_resource(self.name, new_name)

    def set_attributes(self, attributes: Dict[str, str]):
        """Set attributes for the resource and update internal dict."""
        namespace = self.model if not self.is_first_gen else ""
        self._cs_handler.set_resource_attributes(self.name, namespace, attributes)
        self.attributes.update(attributes)

    def get_details(self) -> ResourceInfo:
        """Get resource details."""
        return self._cs_handler.get_resource_details(self.name)

    def refresh_vm_details(self):
        """Refresh VM Details for the App."""
        self.sandbox_handler.refresh_vm_details([self.name])
