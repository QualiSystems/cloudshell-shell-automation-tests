from collections import OrderedDict
from itertools import chain

from shell_tests.helpers import call_exit_func_on_exc, enter_stacks
from shell_tests.resource_handler import ResourceHandler, ServiceHandler


class SandboxHandler(object):
    def __init__(self, name, resource_configs, service_configs, cs_handler, shell_handlers,
                 ftp_handler, logger):
        """Sandbox Handler that creates reservation adds resources.

        :type name: str
        :type resource_configs: list[shell_tests.configs.ResourceConfig]
        :type service_configs: list[shell_tests.configs.ServiceConfig]
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type shell_handlers: OrderedDict[str, shell_tests.shell_handler.ShellHandler]
        :type ftp_handler: shell_tests.ftp_handler.FTPHandler
        :type logger: logging.Logger
        """
        self.name = name
        self.resource_configs = resource_configs
        self.service_configs = service_configs
        self.cs_handler = cs_handler
        self.shell_handlers = shell_handlers
        self.ftp_handler = ftp_handler
        self.logger = logger

        self.reservation_id = None
        self.resource_service_stack = None

        self.resource_handlers = map(self._create_resource_handler, resource_configs)
        self.service_handlers = map(self._create_service_handler, service_configs)

    def _create_resource_handler(self, resource_conf):
        return ResourceHandler.from_conf(
            resource_conf,
            self.cs_handler,
            self,
            self.shell_handlers[resource_conf.shell_name],
            self.logger,
        )

    def _create_service_handler(self, service_conf):
        return ServiceHandler.from_conf(
            service_conf,
            self.cs_handler,
            self,
            self.shell_handlers[service_conf.shell_name],
            self.logger,
        )

    @classmethod
    def from_conf(cls, conf, resource_configs, service_configs, cs_handler, shell_handlers,
                  ftp_handler, logger):
        """Create SandboxHandler from the config and handlers.

        :type conf: shell_tests.configs.SandboxConfig
        :type resource_configs: list[shell_tests.configs.ResourceConfig]
        :type service_configs: list[shell_tests.configs.ServiceConfig]
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type shell_handlers: OrderedDict[str, shell_tests.shell_handler.ShellHandler]
        :type ftp_handler: shell_tests.ftp_handler.FTPHandler
        :type logger: logging.Logger
        """
        return cls(
            conf.name,
            resource_configs,
            service_configs,
            cs_handler,
            shell_handlers,
            ftp_handler,
            logger,
        )

    def create_reservation(self):
        """Create the reservation."""
        self.reservation_id = self.cs_handler.create_reservation(self.name)

    def add_resource_to_reservation(self, resource_name):
        """Add a resource to the reservation.

        :type resource_name: str
        """
        self.cs_handler.add_resource_to_reservation(self.reservation_id, resource_name)

    def add_service_to_reservation(self, service_model, service_name, attributes):
        """Add the service to the reservation.

        :type service_model: str
        :type service_name: str
        :type attributes: dict
        """
        self.cs_handler.add_service_to_reservation(
            self.reservation_id, service_model, service_name, attributes)

    def delete_reservation(self):
        """Delete the reservation."""
        self.cs_handler.delete_reservation(self.reservation_id)

    def execute_resource_command(self, resource_name, command_name, command_kwargs):
        """Execute the command for the resource.

        :type resource_name: str
        :type command_name: str
        :type command_kwargs: dict
        """
        return self.cs_handler.execute_command_on_resource(
            self.reservation_id, resource_name, command_name, command_kwargs)

    def execute_service_command(self, service_name, command_name, command_kwargs):
        """Execute the command for the service.

        :type service_name: str
        :type command_name: str
        :type command_kwargs: dict[str, str]
        """
        return self.cs_handler.execute_command_on_service(
            self.reservation_id, service_name, command_name, command_kwargs)

    @call_exit_func_on_exc
    def __enter__(self):
        self.create_reservation()

        # enter into resources context
        self.resource_service_stack = enter_stacks(chain(
            self.resource_handlers, self.service_handlers,
        ))
        self.resource_service_stack.__enter__()

        for resource_handler in self.resource_handlers:
            self.add_resource_to_reservation(resource_handler.name)

        for service_handler in self.service_handlers:
            self.add_service_to_reservation(
                service_handler.model, service_handler.name, service_handler.attributes)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.reservation_id:
            self.delete_reservation()

        if self.resource_service_stack:
            self.resource_service_stack.__exit__(exc_type, exc_val, exc_tb)

        return False
