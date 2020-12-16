from typing import TYPE_CHECKING

from shell_tests.configs import SandboxConfig
from shell_tests.errors import DeploymentResourceNotFoundError
from shell_tests.handlers.cs_handler import CloudShellHandler, ReservationId

if TYPE_CHECKING:
    from shell_tests.handlers.resource_handler import ResourceHandler, ServiceHandler


class SandboxHandler:
    def __init__(
        self,
        conf: SandboxConfig,
        reservation_id: ReservationId,
        cs_handler: CloudShellHandler,
    ):
        self.conf = conf
        self.reservation_id = reservation_id
        self._cs_handler = cs_handler

    @classmethod
    def create(
        cls, conf: SandboxConfig, cs_handler: CloudShellHandler, duration: int = 2 * 60
    ) -> "SandboxHandler":
        if conf.blueprint_name:
            rid = cs_handler.create_topology_reservation(
                conf.name, conf.blueprint_name, duration, conf.specific_version
            )
        else:
            rid = cs_handler.create_reservation(conf.name, duration)
        try:
            cs_handler.wait_reservation_is_started(rid)
        except BaseException as e:
            cs_handler.end_reservation(rid, conf.name, wait=False)
            raise e
        return cls(conf, rid, cs_handler)

    def add_resource_to_reservation(self, resource_handler: "ResourceHandler"):
        """Add a resource to the reservation."""
        self._cs_handler.add_resource_to_reservation(
            self.reservation_id, resource_handler.name
        )
        resource_handler.sandbox_handler = self

    def add_service_to_reservation(self, service_handler: "ServiceHandler"):
        """Add the service to the reservation."""
        self._cs_handler.add_service_to_reservation(
            self.reservation_id,
            service_handler.model,
            service_handler.name,
            service_handler.attributes,
        )
        service_handler.sandbox_handler = self

    def end_reservation(self, wait: bool = True):
        """End the reservation."""
        return self._cs_handler.end_reservation(
            self.reservation_id, self.conf.name, wait
        )

    def delete_reservation(self):
        """Delete the reservation."""
        self._cs_handler.delete_reservation(self.reservation_id)

    def execute_resource_command(
        self, resource_name: str, command_name: str, command_kwargs: dict[str, str]
    ) -> str:
        """Execute the command for the resource."""
        return self._cs_handler.execute_command_on_resource(
            self.reservation_id, resource_name, command_name, command_kwargs
        )

    def execute_service_command(
        self, service_name: str, command_name: str, command_kwargs: dict[str, str]
    ) -> str:
        """Execute the command for the service."""
        return self._cs_handler.execute_command_on_service(
            self.reservation_id, service_name, command_name, command_kwargs
        )

    def add_physical_connection(self, port_name1: str, port_name2: str):
        """Add physical connection between the ports."""
        self._cs_handler.add_physical_connection(
            self.reservation_id, port_name1, port_name2
        )

    def connect_ports_with_connector(
        self, port_name1: str, port_name2: str, connector_name: str
    ):
        """Connect the ports with a connector."""
        self._cs_handler.connect_ports_with_connector(
            self.reservation_id, port_name1, port_name2, connector_name
        )

    def remove_connector(self, port_name1: str, port_name2: str):
        """Remove the connector between the ports."""
        self._cs_handler.remove_connector(self.reservation_id, port_name1, port_name2)

    def get_deployment_resource_name(self) -> str:
        info = self._cs_handler.get_topology_details(self.conf.blueprint_name)
        assert len(info.Apps) == 1, "Supported only 1 app in the reservation"
        app_name = info.Apps[0].Name
        names = self._cs_handler.get_resources_names_in_reservation(self.reservation_id)
        found_names = []
        for resource_name in names:
            if resource_name.startswith(app_name) or resource_name.startswith(
                app_name.replace(" ", "-")
            ):
                found_names.append(resource_name)
        if len(found_names) > 1:
            raise DeploymentResourceNotFoundError(
                f"There are more than one suitable resource for the name "
                f"{app_name} in the reservation {self.reservation_id}. "
                f"Available resources are {names}"
            )
        elif not found_names:
            raise DeploymentResourceNotFoundError(
                f"Could not find the deployment resource with prefix {app_name} in "
                f"the reservation {self.reservation_id}. "
                f"Available resources are {names}"
            )
        else:
            return found_names[0]

    def wait_for_started(self):
        self._cs_handler.wait_reservation_is_started(self.reservation_id)

    def refresh_vm_details(self, app_names: list[str]):
        self._cs_handler.refresh_vm_details(self.reservation_id, app_names)

    def finish(self):
        self.end_reservation()
