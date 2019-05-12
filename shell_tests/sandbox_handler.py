import re
from collections import OrderedDict
from itertools import chain

from shell_tests.errors import DeploymentResourceNotFoundError
from shell_tests.helpers import call_exit_func_on_exc, enter_stacks


class SandboxHandler(object):
    def __init__(self, name, blueprint_name, tests_conf, resource_handlers,
                 deployment_resource_handlers, service_handlers, cs_handler, shell_handlers,
                 ftp_handler, vcenter_handler, blueprint_handler, logger):
        """Sandbox Handler that creates reservation adds resources.

        :type name: str
        :type blueprint_name: str
        :type tests_conf: shell_tests.configs.TestsConfig
        :type resource_handlers: list[shell_tests.resource_handler.ResourceHandler]
        :type deployment_resource_handlers: list[shell_tests.resource_handler.DeploymentResourceHandler]
        :type service_handlers: list[shell_tests.resource_handler.ServiceHandler]
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type shell_handlers: OrderedDict[str, shell_tests.shell_handler.ShellHandler]
        :type ftp_handler: shell_tests.ftp_handler.FTPHandler
        :type vcenter_handler: shell_tests.vcenter_handler.VcenterHandler
        :type blueprint_handler: shell_tests.blueprint_handler.BlueprintHandler
        :type logger: logging.Logger
        """
        self.name = name
        self.blueprint_name = blueprint_name
        self.tests_conf = tests_conf
        self.resource_handlers = resource_handlers
        self.deployment_resource_handlers = deployment_resource_handlers
        self.service_handlers = service_handlers
        self.cs_handler = cs_handler
        self.shell_handlers = shell_handlers
        self.ftp_handler = ftp_handler
        self.vcenter_handler = vcenter_handler
        self.blueprint_handler = blueprint_handler
        self.logger = logger

        self.reservation_id = None
        self.resource_service_stack = None
        self._stacks = None

        for deployment_resource_handler in self.deployment_resource_handlers:
            deployment_resource_handler.sandbox_handler = self

    @classmethod
    def from_conf(cls, conf, resource_handlers, deployment_resource_handlers, service_handlers,
                  cs_handler, shell_handlers, ftp_handler, vcenter_handler, blueprint_handler, logger):
        """Create SandboxHandler from the config and handlers.

        :type conf: shell_tests.configs.SandboxConfig
        :type resource_handlers: list[shell_tests.resource_handler.ResourceHandler]
        :type deployment_resource_handlers: list[shell_tests.resource_handler.DeploymentResourceHandler]
        :type service_handlers: list[shell_tests.resource_handler.ServiceHandler]
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type shell_handlers: OrderedDict[str, shell_tests.shell_handler.ShellHandler]
        :type ftp_handler: shell_tests.ftp_handler.FTPHandler
        :type vcenter_handler: shell_tests.vcenter_handler.VcenterHandler
        :type blueprint_handler: shell_tests.blueprint_handler.BlueprintHandler
        :type logger: logging.Logger
        """
        return cls(
            conf.name,
            conf.blueprint_name,
            conf.tests_conf,
            resource_handlers,
            deployment_resource_handlers,
            service_handlers,
            cs_handler,
            shell_handlers,
            ftp_handler,
            vcenter_handler,
            blueprint_handler,
            logger,
        )

    def create_reservation(self, duration=2*60):
        """Create the reservation."""
        if self.blueprint_name:
            rid = self.cs_handler.create_topology_reservation(self.name, self.blueprint_name, duration)
        else:
            rid = self.cs_handler.create_reservation(self.name, duration)

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

    def add_physical_connection(self, port_name1, port_name2):
        """Add physical connection between the ports.

        :type port_name1:str
        :type port_name2: str
        """
        self.cs_handler.add_physical_connection(self.reservation_id, port_name1, port_name2)

    def connect_ports_with_connector(self, port_name1, port_name2, connector_name):
        """Connect the ports with a connector.

        :type port_name1: str
        :type port_name2: str
        :type connector_name: str
        """
        self.cs_handler.connect_ports_with_connector(
            self.reservation_id, port_name1, port_name2, connector_name)

    def remove_connector(self, port_name1, port_name2):
        """Remove the connector between the ports.

        :type port_name1: str
        :type port_name2: str
        """
        self.cs_handler.remove_connector(self.reservation_id, port_name1, port_name2)

    def get_deployment_resource_name(self, blueprint_name):
        names = self.cs_handler.get_resources_names_in_reservation(self.reservation_id)
        for resource_name in names:
            if re.search(
                    r'^{}_\w{{4}}-\w{{4}}$'.format(blueprint_name),
                    resource_name,
            ):
                return resource_name

        raise DeploymentResourceNotFoundError(
            'Could not find the deployment resource with prefix {} in the reservation {}. '
            'Available resources are {}'.format(blueprint_name, self.reservation_id, names)
        )

    @call_exit_func_on_exc
    def __enter__(self):
        self.create_reservation()

        self._stacks = enter_stacks(self.deployment_resource_handlers)
        self._stacks.__enter__()

        for resource_handler in self.resource_handlers:
            self.add_resource_to_reservation(resource_handler)

        for service_handler in self.service_handlers:
            self.add_service_to_reservation(service_handler)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._stacks:
            self._stacks.__exit__(exc_type, exc_val, exc_tb)

        if self.reservation_id:
            self.end_reservation()
            self.delete_reservation()

        for target_handler in chain(self.resource_handlers, self.service_handlers):
            target_handler.sandbox_handler = None

        return False
