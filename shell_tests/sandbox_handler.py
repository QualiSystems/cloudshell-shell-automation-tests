from collections import OrderedDict

from shell_tests.helpers import call_exit_func_on_exc, enter_stacks
from shell_tests.resource_handler import ResourceHandler


class SandboxHandler(object):
    def __init__(self, name, resource_names, resource_configs, cs_handler, shell_handlers, logger):
        """Sandbox Handler that creates reservation adds resources.

        :type name: str
        :type resource_names: list[str]
        :param resource_names: names of resources that included into the sandbox
        :type resource_configs: OrderedDict[str, shell_tests.configs.ResourceConfig]
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type shell_handlers: OrderedDict[str, shell_tests.shell_handler.ShellHandler]
        :type logger: logging.Logger
        """
        self.name = name
        self.resource_configs = resource_configs
        self.cs_handler = cs_handler
        self.shell_handlers = shell_handlers
        self.logger = logger

        self.reservation_id = None
        self.resources_stack = None

        self.resources = OrderedDict(
            (resource_name, self._create_resource_handler(resource_configs[resource_name]))
            for resource_name in resource_names
        )

    def _create_resource_handler(self, resource_conf):
        return ResourceHandler.from_conf(
            resource_conf,
            self.cs_handler,
            self,
            self.shell_handlers[resource_conf.shell_name],
            self.logger,
        )

    @classmethod
    def from_config(cls, conf, resource_configs, cs_handler, shell_handlers, logger):
        """Create SandboxHandler from the config and handlers.

        :type conf: shell_tests.configs.SandboxConfig
        :type resource_configs: OrderedDict[str, shell_tests.configs.ResourceConfig]
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type shell_handlers: OrderedDict[str, shell_tests.shell_handler.ShellHandler]
        :type logger: logging.Logger
        """
        return cls(
            conf.name,
            conf.resource_names,
            resource_configs,
            cs_handler,
            shell_handlers,
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

    @call_exit_func_on_exc
    def __enter__(self):
        self.create_reservation()

        # enter into resources context
        self.resources_stack = enter_stacks(self.resources.values()).__enter__()
        for resource_name in self.resources.keys():
            self.add_resource_to_reservation(resource_name)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.reservation_id:
            self.delete_reservation()

        if self.resources_stack:
            self.resources_stack.__exit__(exc_type, exc_val, exc_tb)

        return False
