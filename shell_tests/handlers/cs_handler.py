import re
import time
from functools import cached_property
from pathlib import Path
from typing import Dict, List, Tuple, TypeVar

from cloudshell.api.cloudshell_api import (
    AttributeNameValue,
    CloudShellAPISession,
    GetReservationDescriptionResponseInfo,
    InputNameValue,
    ReservationSlimStatus,
    ResourceAttributesUpdateRequest,
    ResourceInfo,
    SetConnectorRequest,
    TopologyInfo,
    UpdateTopologyGlobalInputsRequest,
)
from cloudshell.api.common_cloudshell_api import CloudShellAPIError
from cloudshell.rest.api import PackagingRestApiClient
from urllib3.exceptions import MaxRetryError

from shell_tests.configs import CloudShellConfig
from shell_tests.errors import (
    BaseAutomationException,
    CreationReservationError,
    CSIsNotAliveError,
)
from shell_tests.helpers.cs_helpers import generate_new_resource_name
from shell_tests.helpers.cs_http import get_reservation_errors
from shell_tests.helpers.logger import logger

ReservationId = TypeVar("ReservationId", bound=str)


class CloudShellHandler:
    def __init__(self, conf: CloudShellConfig):
        self.conf = conf

    @cached_property
    def _rest_api(self) -> PackagingRestApiClient:
        logger.debug("Connecting to REST API")
        rest_api = PackagingRestApiClient(
            self.conf.host, 9000, self.conf.user, self.conf.password, self.conf.domain
        )
        logger.debug("Connected to REST API")
        return rest_api

    @cached_property
    def _api(self) -> CloudShellAPISession:
        logger.debug("Connecting to Automation API")
        api = CloudShellAPISession(
            self.conf.host, self.conf.user, self.conf.password, self.conf.domain
        )
        logger.debug("Connected to Automation API")
        return api

    def wait_for_cs_is_started(self):
        for _ in range(10):
            try:
                _ = self._api
            except (OSError, MaxRetryError):
                time.sleep(10)
            else:
                break
        else:
            logger.warning(f"CloudShell {self.conf.host} is not alive")
            raise CSIsNotAliveError

    def install_shell(self, shell_path: Path):
        shell_name = shell_path.name
        shell_path = str(shell_path)
        logger.info(f"Installing the Shell {shell_name}")
        try:
            self._rest_api.add_shell(shell_path)
            logger.debug("Installed the new Shell")
        except Exception as e:
            err_msg = e.args[0] if e.args else ""
            if "already exists" not in err_msg:
                raise e

            shell_name = re.search(
                "named '(?P<name>.+)' already exists", err_msg,
            ).group("name")

            self._rest_api.update_shell(shell_path, shell_name)
            logger.debug(f"Updated {shell_name} Shell")

    def remove_shell(self, shell_name: str):
        logger.info(f"Deleting the Shell {shell_name}")
        self._rest_api.delete_shell(shell_name)
        logger.debug(f"The Shell {shell_name} is deleted")

    def import_package(self, package_path: Path):
        """Import the package to the CloudShell."""
        package_path = str(package_path)
        logger.info(f"Importing a package {package_path} to the CloudShell")
        self._rest_api.import_package(package_path)
        logger.debug("Imported the package")

    def create_reservation(self, name: str, duration: int = 120) -> ReservationId:
        """Create reservation, returns uuid."""
        logger.info(f"Creating the reservation {name}")
        resp = self._api.CreateImmediateReservation(name, self._api.username, duration)
        return resp.Reservation.Id

    def create_topology_reservation(
        self,
        name: str,
        topology_name: str,
        duration: int = 24 * 60,
        specific_version: str = "",
    ) -> ReservationId:
        """Create topology reservation, return uuid."""
        if specific_version:
            global_input_req = [
                UpdateTopologyGlobalInputsRequest("Version", specific_version)
            ]
        else:
            global_input_req = []

        str_specific_version = f" - {specific_version}" if specific_version else ""
        logger.info(
            f"Creating a topology reservation {name} for "
            f"{topology_name}{str_specific_version}"
        )
        resp = self._api.CreateImmediateTopologyReservation(
            name,
            self._api.username,
            duration,
            topologyFullPath=topology_name,
            globalInputs=global_input_req,
        )
        return resp.Reservation.Id

    def wait_reservation_is_started(self, reservation_id: ReservationId):
        for _ in range(60):
            status = self.get_reservation_status(reservation_id)
            if (
                status.ProvisioningStatus == "Ready"
                or status.ProvisioningStatus == "Not Run"
                and status.Status == "Started"
            ):
                break
            elif status.ProvisioningStatus == "Error":
                errors = self._get_reservation_errors(reservation_id)
                logger.error(
                    f"Reservation {reservation_id} started with errors: {errors}"
                )
                raise CreationReservationError(errors)
            time.sleep(30)
        else:
            raise CreationReservationError(
                f"The reservation {reservation_id} doesn't started"
            )
        logger.debug("The reservation created")

    def _get_reservation_errors(
        self, reservation_id: ReservationId
    ) -> List[Tuple[str, str]]:
        """Get error messages from activity tab in reservation."""
        errors = get_reservation_errors(self.conf, reservation_id)
        return list(errors)

    def create_resource(
        self,
        name: str,
        model: str,
        address: str,
        family: str = "",
        parent_path: str = "",
    ) -> str:
        """Create resource, can be generated new name if current is exists."""
        logger.info(f"Creating the resource {name}")
        logger.debug(f"{name=}, {model=}, {address=}, {family=}, {parent_path=}")
        while True:
            try:
                self._api.CreateResource(
                    family, model, name, address, parentResourceFullPath=parent_path
                )
            except CloudShellAPIError as e:
                if str(e.code) != "114":
                    raise
                name = generate_new_resource_name(name)
            else:
                break
        logger.debug(f"Created the resource {name}")
        return name

    def rename_resource(self, current_name: str, new_name: str) -> str:
        """Rename resource, can be generated new name if current is exists."""
        logger.info(f'Renaming resource "{current_name}" to "{new_name}"')
        while True:
            try:
                self._api.RenameResource(current_name, new_name)
            except CloudShellAPIError as e:
                if str(e.code) != "114":
                    raise
                new_name = generate_new_resource_name(new_name)
            else:
                break
        logger.debug(f'Resource "{current_name}" renamed to "{new_name}"')
        return new_name

    def set_resource_attributes(
        self, resource_name: str, namespace: str, attributes: Dict[str, str]
    ):
        """Set attributes for the resource."""
        logger.info(f"Setting attributes for {resource_name}\n{attributes}")
        namespace += "." if namespace else ""
        attributes = [
            AttributeNameValue(f"{namespace}{key}", value)
            for key, value in attributes.items()
        ]
        self._api.SetAttributesValues(
            [ResourceAttributesUpdateRequest(resource_name, attributes)]
        )

    def get_resource_commands(self, resource_name: str) -> List[str]:
        logger.info(f"Get commands for the resource {resource_name}")
        resp = self._api.GetResourceCommands(resource_name)
        return [command.Name for command in resp.Commands]

    def resource_autoload(self, resource_name: str):
        """Start autoload for the resource."""
        logger.info(f"Start Autoload for the {resource_name}")
        self._api.AutoLoad(resource_name)
        logger.debug("Finished Autoload")

    def update_driver_for_the_resource(self, resource_name: str, driver_name: str):
        """Update driver for the resource."""
        logger.info(f'Update Driver "{driver_name}" for the Resource "{resource_name}"')
        self._api.UpdateResourceDriver(resource_name, driver_name)

    def add_resource_to_reservation(
        self, reservation_id: ReservationId, resource_name: str
    ):
        """Adding the resource to the reservation."""
        logger.info(
            f"Adding a resource {resource_name} to a reservation {reservation_id}"
        )
        self._api.AddResourcesToReservation(reservation_id, [resource_name])
        logger.debug("Added a resource to the reservation")

    def add_service_to_reservation(
        self,
        reservation_id: ReservationId,
        service_model: str,
        service_name: str,
        attributes: Dict[str, str],
    ):
        """Add the service to the reservation."""
        logger.info(
            f"Adding a service {service_name} to a reservation {reservation_id}"
        )
        attributes = [
            AttributeNameValue(f"{service_model}.{key}", value)
            for key, value in attributes.items()
        ]
        self._api.AddServiceToReservation(
            reservation_id, service_model, service_name, attributes
        )
        logger.debug("Added the service to the reservation")

    def delete_resource(self, resource_name: str):
        """Delete the resource."""
        logger.info(f"Deleting a resource {resource_name}")
        self._api.DeleteResource(resource_name)
        logger.debug("Deleted a resource")

    def delete_reservation(self, reservation_id: ReservationId):
        """Delete the reservation."""
        logger.info(f"Deleting the reservation {reservation_id}")
        self._api.DeleteReservation(reservation_id)
        logger.debug("Deleted the reservation")

    def end_reservation(self, reservation_id: ReservationId, wait: bool = True):
        """End the reservation."""
        logger.info(f"Ending a reservation for {reservation_id}")
        self._api.EndReservation(reservation_id)
        if wait:
            for _ in range(30):
                status = self.get_reservation_status(reservation_id).Status
                if status == "Completed":
                    break
                time.sleep(30)
            else:
                raise BaseAutomationException("Can't end reservation")
            logger.info("Reservation ended")

    def _execute_command(
        self,
        reservation_id: ReservationId,
        target_name: str,
        target_type: str,  # Service or Resource
        command_name: str,
        command_kwargs: Dict[str, str],
    ) -> str:
        """Execute a command on the target."""
        logger.debug(
            f"Executing command {command_name} with kwargs {command_kwargs} for the "
            f"target {target_name} in the reservation {reservation_id}"
        )
        command_kwargs = [
            InputNameValue(key, value) for key, value in command_kwargs.items()
        ]
        resp = self._api.ExecuteCommand(
            reservation_id, target_name, target_type, command_name, command_kwargs, True
        )
        logger.debug(f"Executed command, output {resp.Output}")
        return resp.Output

    def execute_command_on_resource(
        self,
        reservation_id: ReservationId,
        resource_name: str,
        command_name: str,
        command_kwargs: Dict[str, str],
    ) -> str:
        """Execute a command on the resource."""
        return self._execute_command(
            reservation_id, resource_name, "Resource", command_name, command_kwargs
        )

    def execute_command_on_service(
        self,
        reservation_id: ReservationId,
        service_name: str,
        command_name: str,
        command_kwargs: Dict[str, str],
    ) -> str:
        """Execute a command for the service."""
        return self._execute_command(
            reservation_id, service_name, "Service", command_name, command_kwargs
        )

    def get_resource_details(self, resource_name: str) -> ResourceInfo:
        """Get resource details."""
        logger.info(f"Getting resource details for {resource_name}")
        output = self._api.GetResourceDetails(resource_name)
        logger.debug(f"Got details {output}")
        return output

    def get_topologies_by_category(self, category_name: str) -> List[str]:
        """Get available topology names by category name."""
        logger.info(f"Getting topologies for a category {category_name}")
        output = self._api.GetTopologiesByCategory(category_name).Topologies
        logger.debug(f"Got topologies {sorted(output)}")
        return output

    def get_topology_details(self, topology_name: str) -> TopologyInfo:
        logger.info(f"Getting details for the topology {topology_name}")
        output = self._api.GetTopologyDetails(topology_name)
        return output

    def get_reservation_details(
        self, reservation_id: ReservationId
    ) -> GetReservationDescriptionResponseInfo:
        """Get reservation details."""
        logger.info(f"Getting reservation details for the {reservation_id}")
        output = self._api.GetReservationDetails(reservation_id)
        logger.debug(f"Got reservation details {output}")
        return output

    def get_reservation_status(
        self, reservation_id: ReservationId
    ) -> ReservationSlimStatus:
        """Check that the reservation ready."""
        logger.debug(f"Getting reservation status for a {reservation_id}")
        output = self._api.GetReservationStatus(reservation_id).ReservationSlimStatus
        logger.debug(f"Got status {output}")
        return output

    def add_physical_connection(
        self, reservation_id: ReservationId, port1: str, port2: str
    ):
        """Add physical connection between two ports.

        :param reservation_id:
        :param port1: ex, Cisco-IOS-device/Chassis 0/FastEthernet0-1
        :param port2: ex, Cisco-IOS-device-1/Chassis 0/FastEthernet0-10
        """
        logger.info(f"Create physical connection between {port1} and {port2}")
        self._api.UpdatePhysicalConnection(port1, port2)
        self._api.AddRoutesToReservation(reservation_id, [port1], [port2], "bi")

    def connect_ports_with_connector(
        self, reservation_id: ReservationId, port1: str, port2: str, connector_name: str
    ):
        """Connect two ports with connector."""
        logger.info(f"Creating connector between {port1} and {port2}")
        connector = SetConnectorRequest(port1, port2, "bi", connector_name)
        self._api.SetConnectorsInReservation(reservation_id, [connector])
        self._api.ConnectRoutesInReservation(reservation_id, [port1, port2], "bi")

    def remove_connector(self, reservation_id: ReservationId, port1: str, port2: str):
        """Remove connector between ports."""
        logger.info(f"Removing connector between {port1} and {port2}")
        self._api.DisconnectRoutesInReservation(reservation_id, [port1, port2])
        self._api.RemoveConnectorsFromReservation(reservation_id, [port1, port2])

    def get_resources_names_in_reservation(
        self, reservation_id: ReservationId
    ) -> List[str]:
        """Get resources names in the reservation."""
        logger.info(f"Get resources names in the reservation {reservation_id}")
        resources_info = self._api.GetReservationResourcesPositions(
            reservation_id
        ).ResourceDiagramLayouts
        names = [resource.ResourceName for resource in resources_info]
        logger.info(f"Resources names are: {names}")
        return names

    def refresh_vm_details(self, reservation_id: ReservationId, app_names: List[str]):
        """Refresh VM Details."""
        logger.info(f'Refresh VM Details for the "{app_names}"')
        self._api.RefreshVMDetails(reservation_id, app_names)
        logger.debug("VM Details are refreshed")
