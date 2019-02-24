from collections import OrderedDict
from itertools import chain

from shell_tests.helpers import call_exit_func_on_exc


class SandboxHandler(object):
    def __init__(self, name, blueprint_name, resource_handlers, service_handlers, cs_handler,
                 shell_handlers, ftp_handler, logger):
        """Sandbox Handler that creates reservation adds resources.

        :type name: str
        :type blueprint_name: str
        :type resource_handlers: list[shell_tests.resource_handler.ResourceHandler]
        :type service_handlers: list[shell_tests.resource_handler.ServiceHandler]
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type shell_handlers: OrderedDict[str, shell_tests.shell_handler.ShellHandler]
        :type ftp_handler: shell_tests.ftp_handler.FTPHandler
        :type logger: logging.Logger
        """
        self.name = name
        self.blueprint_name = blueprint_name
        self.resource_handlers = resource_handlers
        self.service_handlers = service_handlers
        self.cs_handler = cs_handler
        self.shell_handlers = shell_handlers
        self.ftp_handler = ftp_handler
        self.logger = logger

        self.reservation_id = None
        self.resource_service_stack = None

    @classmethod
    def from_conf(cls, conf, resource_handlers, service_handlers, cs_handler, shell_handlers,
                  ftp_handler, logger):
        """Create SandboxHandler from the config and handlers.

        :type conf: shell_tests.configs.SandboxConfig
        :type resource_handlers: list[shell_tests.resource_handler.ResourceHandler]
        :type service_handlers: list[shell_tests.resource_handler.ServiceHandler]
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type shell_handlers: OrderedDict[str, shell_tests.shell_handler.ShellHandler]
        :type ftp_handler: shell_tests.ftp_handler.FTPHandler
        :type logger: logging.Logger
        """
        return cls(
            conf.name,
            conf.blueprint_name,
            resource_handlers,
            service_handlers,
            cs_handler,
            shell_handlers,
            ftp_handler,
            logger,
        )

    def create_reservation(self):
        """Create the reservation."""
        if self.blueprint_name:
            rid = self.cs_handler.create_topology_reservation(self.name, self.blueprint_name)
        else:
            rid = self.cs_handler.create_reservation(self.name)

        self.reservation_id = rid

    def add_resource_to_reservation(self, resource_handler):
        """Add a resource to the reservation.

        :type resource_handler: shell_tests.resource_handler.ResourceHandler
        """
        self.cs_handler.add_resource_to_reservation(self.reservation_id, resource_handler.name)
        resource_handler.sandbox_handler = self

    def add_service_to_reservation(self, service_handler):
        """Add the service to the reservation.

        :type service_handler: shell_tests.resource_handler.ServiceHandler
        """
        self.cs_handler.add_service_to_reservation(
            self.reservation_id,
            service_handler.model,
            service_handler.name,
            service_handler.attributes,
        )
        service_handler.sandbox_handler = self

    def end_reservation(self):
        """End the reservation."""
        return self.cs_handler.end_reservation(self.reservation_id)

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

        for resource_handler in self.resource_handlers:
            self.add_resource_to_reservation(resource_handler)

        for service_handler in self.service_handlers:
            self.add_service_to_reservation(service_handler)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.reservation_id:
            self.end_reservation()
            self.delete_reservation()

        for target_handler in chain(self.resource_handlers, self.service_handlers):
            target_handler.sandbox_handler = None

        return False
