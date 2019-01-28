from collections import OrderedDict

from shell_tests.resource_handler import ResourceHandler


class SandboxHandler(object):
    def __init__(self, name, resource_names, resource_configs, cs_handler, shell_handlers, logger):
        """Sandbox Handler that creates reservation adds resources.

        :type name: str
        :type resource_names: list[str]
        :param resource_names: names of resources that included into the sandbox
        :type resource_configs: list[shell_tests.configs.ResourceConfig]
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type shell_handlers: dict[str, shell_tests.shell_handler.ShellHandler]
        :type logger: logging.Logger
        """
        self.name = name
        self.resource_names = resource_names
        self.resource_configs = resource_configs
        self.cs_handler = cs_handler
        self.shell_handlers = shell_handlers  # todo change it to dict
        self.logger = logger

        self.reservation_id = None
        self.resources = OrderedDict()

        ResourceHandler.from_conf()
        # todo create resource handlers

    def create_reservation(self):
        """Create the reservation."""
        self.reservation_id = self.cs_handler.create_reservation(self.name)

    def add_resource_to_reservation(self, resource_name):
        """Add a resource to the reservation.

        :type resource_name: str
        """
        self.cs_handler.add_resource_to_reservation(self.reservation_id, resource_name)

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

    def __enter__(self):
        self.create_reservation()
