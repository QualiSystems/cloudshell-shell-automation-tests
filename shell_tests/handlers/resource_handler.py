from enum import Enum
from functools import cached_property
from typing import Optional

from cloudshell.api.cloudshell_api import ResourceInfo
from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.configs import (
    AdditionalPort,
    DeploymentResourceConfig,
    ResourceCommand,
    ResourceConfig,
    ServiceConfig,
)
from shell_tests.errors import BaseAutomationException, DependenciesBrokenError
from shell_tests.handlers.cs_handler import CloudShellHandler
from shell_tests.handlers.sandbox_handler import SandboxHandler
from shell_tests.handlers.shell_handler import ShellHandler
from shell_tests.helpers.logger import logger


class DeviceType(Enum):
    REAL_DEVICE = "Real device"
    SIMULATOR = "Simulator"
    WITHOUT_DEVICE = "Without device"
    SHELL_FROM_TEMPLATE = "Shell from template"


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
        self.children_attributes = {}
        self._cs_handler = cs_handler
        self._shell_handler = shell_handler

        self.is_autoload_finished = False
        self.dependencies_are_broken = False
        self._sandbox_handler = None

    @classmethod
    def create(
        cls,
        conf: ResourceConfig,
        cs_handler: CloudShellHandler,
        shell_handler: ShellHandler,
    ) -> "ResourceHandler":
        logger.info(f"Start preparing the resource {conf.name}")
        resource = cls(conf, cs_handler, shell_handler)
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
        if "SHELL_FROM_TEMPLATE" in self.conf.name:
            return DeviceType.SHELL_FROM_TEMPLATE
        elif not self.conf.device_ip:
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

    def set_attributes(self, attributes: dict[str, str]):
        """Set attributes for the resource and update internal dict."""
        namespace = self.model if not self.conf.is_first_gen else ""
        self._cs_handler.set_resource_attributes(self.name, namespace, attributes)
        self.attributes.update(attributes)

    def set_children_attributes(self, children_attributes: dict[str, dict[str, str]]):
        """Set children attributes."""
        for child_name, attributes in children_attributes.items():
            child_name = f"{self.name}/{child_name}"
            child_info = self._cs_handler.get_resource_details(child_name)

            for attribute_name, attribute_value in attributes.items():
                self._set_child_attribute(child_info, attribute_name, attribute_value)

    def _set_child_attribute(
        self, child_info: ResourceInfo, attribute_name: str, attribute_value: str
    ):
        namespace = child_info.ResourceModelName
        for attribute_info in child_info.ResourceAttributes:
            namespace, name = attribute_info.Name.rsplit(".", 1)
            if name == attribute_name:
                break
        self._cs_handler.set_resource_attributes(
            child_info.Name, namespace, {attribute_name: attribute_value}
        )

    def _autoload(self, name: str):
        try:
            return self._cs_handler.resource_autoload(name)
        except DependenciesBrokenError:
            self.dependencies_are_broken = True
            raise

    def autoload(self):
        """Run Autoload for the resource."""
        try:
            self._autoload(self.name)
        except CloudShellAPIError as e:
            if str(e.code) != "129" and e.message != "no driver associated":
                raise
            self._cs_handler.update_driver_for_the_resource(self.name, self.model)
            self._autoload(self.name)

        if self.conf.additional_ports:
            self._add_additional_ports(self.conf.additional_ports)
        if self.conf.children_attributes:
            self.set_children_attributes(self.conf.children_attributes)
        self.is_autoload_finished = True

    def get_details(self) -> ResourceInfo:
        """Get resource details."""
        return self._cs_handler.get_resource_details(self.name)

    def get_commands(self) -> list[str]:
        return self._cs_handler.get_resource_commands(self.name)

    def execute_command(self, command_name: str, command_kwargs: dict[str, str]) -> str:
        """Execute the command for the resource."""
        try:
            output = self.sandbox_handler.execute_resource_command(
                self.name, command_name, command_kwargs
            )
        except DependenciesBrokenError:
            self.dependencies_are_broken = True
            raise
        return output

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

    def run_resource_commands(self, commands: list[ResourceCommand]):
        for command in commands:
            if command.mode is command.mode.CONFIG:
                self.run_custom_config_command(command.command)
            else:
                self.run_custom_command(command.command)

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
            "orchestration_save", {"mode": mode, "custom_params": custom_params}
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

    def _add_additional_ports(self, additional_port_configs: list[AdditionalPort]):
        info = self.get_details()
        for child_res in info.ChildResources:
            if child_res.ResourceFamilyName == "CS_Chassis":
                chassis_name = child_res.Name
                break
        else:
            _name = self._cs_handler.create_resource(
                name="Chassis 1",
                model=f"{info.ResourceModelName}.GenericChassis",
                address="CH1",
                family="CS_Chassis",
                parent_path=info.Name,
            )
            chassis_name = f"{info.Name}/{_name}"

        for i, port_conf in enumerate(additional_port_configs, 1):
            self._cs_handler.create_resource(
                name=port_conf.name,
                model=f"{info.ResourceModelName}.GenericPort",
                address=f"P{i}",
                family="CS_Port",
                parent_path=chassis_name,
            )

    def finish(self):
        self._cs_handler.delete_resource(self.name)


class ServiceHandler:
    def __init__(self, name: str, attributes: dict[str, str], model: str):
        self.name = name
        self.model = model
        self.family = None
        self.attributes = attributes

        self._sandbox_handler = None

    @classmethod
    def from_conf(cls, conf: ServiceConfig) -> "ServiceHandler":
        return cls(conf.name, conf.attributes, conf.model)

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

    def execute_command(self, command_name: str, command_kwargs: dict[str, str]) -> str:
        """Execute the command for the service."""
        return self.sandbox_handler.execute_service_command(
            self.name, command_name, command_kwargs
        )

    def load_config(self, config_path: str, extra_kwargs: Optional[dict] = None) -> str:
        """Execute a command load_config for the service."""
        extra_kwargs = extra_kwargs or {}
        extra_kwargs.update({"config_file_location": config_path})
        return self.execute_command("load_config", extra_kwargs)

    def start_traffic(self, extra_kwargs: Optional[dict] = None) -> str:
        """Execute a command start traffic for the service."""
        return self.execute_command("start_traffic", extra_kwargs or {})

    def stop_traffic(self, extra_kwargs: Optional[dict] = None) -> str:
        """Execute a command stop traffic for the service."""
        return self.execute_command("stop_traffic", extra_kwargs or {})

    def get_statistics(self, extra_kwargs: Optional[dict] = None) -> str:
        """Execute a command get statistics for the service."""
        return self.execute_command("get_statistics", extra_kwargs or {})

    def get_test_file(self, test_name: str) -> str:
        """Execute a command get test file for the service."""
        return self.execute_command("get_test_file", {"test_name": test_name})


class DeploymentResourceHandler:
    def __init__(
        self,
        conf: DeploymentResourceConfig,
        vm_name: str,
        sandbox_handler: SandboxHandler,
    ):
        self.conf = conf
        self.name = vm_name
        self.vm_name = vm_name
        self.attributes = {}
        self._sandbox_handler = sandbox_handler
        self._cs_handler = sandbox_handler._cs_handler

    @classmethod
    def create_resource(
        cls, conf: DeploymentResourceConfig, sandbox_handler: SandboxHandler
    ) -> "DeploymentResourceHandler":
        logger.info(f"Start preparing the resource {conf.name}")
        vm_name = sandbox_handler.get_deployment_resource_name()
        resource = cls(conf, vm_name, sandbox_handler)
        if conf.attributes:
            resource.set_attributes(conf.attributes)
        logger.info(f"The resource {resource.name} prepared")
        return resource

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

    def set_attributes(self, attributes: dict[str, str]):
        """Set attributes for the resource and update internal dict."""
        namespace = self.model if not self.conf.is_first_gen else ""
        self._cs_handler.set_resource_attributes(self.name, namespace, attributes)
        self.attributes.update(attributes)

    def get_details(self) -> ResourceInfo:
        """Get resource details."""
        return self._cs_handler.get_resource_details(self.name)

    def refresh_vm_details(self):
        """Refresh VM Details for the App."""
        self._sandbox_handler.refresh_vm_details([self.name])
