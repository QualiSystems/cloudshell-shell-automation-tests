import os
import re
import shutil

from cloudshell.api.cloudshell_api import CloudShellAPISession, ResourceAttributesUpdateRequest, \
    AttributeNameValue, InputNameValue, SetConnectorRequest, UpdateTopologyGlobalInputsRequest
from cloudshell.api.common_cloudshell_api import CloudShellAPIError
from cloudshell.rest.api import PackagingRestApiClient

from shell_tests.smb_handler import SMB


class CloudShellHandler(object):
    REST_API_PORT = 9000
    CLOUDSHELL_SERVER_NAME = 'User-PC'
    CS_SHARE = 'C$'
    PYPI_PATH = r'Program Files (x86)\QualiSystems\CloudShell\Server\Config\Pypi Server Repository'
    CS_LOGS_DIR = 'cs_logs'
    CS_LOGS_SHELL_DIR = r'ProgramData\QualiSystems\logs'
    CS_LOGS_INSTALLATION_DIR = (r'Program Files (x86)\QualiSystems\TestShell\ExecutionServer'
                                r'\Logs\QsPythonDriverHost')
    TOSCA_STANDARDS_DIR = r'Program Files (x86)\QualiSystems\CloudShell\Server\ToscaStandard'

    def __init__(self, host, user, password, os_user, os_password, domain, logger):
        """Handler for a CloudShell.

        :param str host: CloudShell ip
        :param str user: CloudShell admin user
        :param str password: password for user
        :param str os_user: OS user
        :param str os_password: OS password
        :param str domain: CloudShell domain
        :param logging.Logger logger:
        """
        self.host = host
        self.user = user
        self.password = password
        self.os_user = os_user
        self.os_password = os_password
        self.domain = domain
        self.logger = logger

        self._smb = None
        self._api = None
        self._rest_api = None

    @classmethod
    def from_conf(cls, conf, logger):
        """Create CloudShell Handler from the config.

        :type conf: shell_tests.configs.CloudShellConfig
        :type logger: logging.Logger
        """
        return cls(
            conf.host,
            conf.user,
            conf.password,
            conf.os_user,
            conf.os_password,
            conf.domain,
            logger,
        )

    @property
    def rest_api(self):
        if self._rest_api is None:
            self.logger.debug('Connecting to REST API')
            self._rest_api = PackagingRestApiClient(
                self.host, self.REST_API_PORT, self.user, self.password, self.domain)
            self.logger.debug('Connected to REST API')
        return self._rest_api

    @property
    def api(self):
        if self._api is None:
            self.logger.debug('Connecting to Automation API')
            self._api = CloudShellAPISession(self.host, self.user, self.password, self.domain)
            self.logger.debug('Connected to Automation API')
        return self._api

    @property
    def smb_handler(self):
        if self._smb is None and self.os_user:
            self._smb = SMB(
                self.os_user,
                self.os_password,
                self.host,
                self.CLOUDSHELL_SERVER_NAME,
                self.logger,
            )

        return self._smb

    def install_shell(self, shell_path):
        """Install Shell driver in the CloudShell

        :param str shell_path: path to shell in zip file
        """

        self.logger.info('Installing the Shell {}'.format(shell_path))

        try:
            self.rest_api.add_shell(shell_path)
            self.logger.debug('Installed the new Shell')
        except Exception as e:
            if 'already exists' not in e.message:
                raise e

            shell_name = re.search(
                "named '(?P<name>.+)' already exists",
                e.message,
            ).group('name')

            self.rest_api.update_shell(shell_path, shell_name)
            self.logger.debug('Updated {} Shell'.format(shell_name))

    def add_cs_standard(self, standard_path):
        """Put standard into tosca standards' dir.

        :type standard_path: str"""
        standard_name = os.path.basename(standard_path)
        remote_standard_path = os.path.join(self.TOSCA_STANDARDS_DIR, standard_name)
        self.logger.warning('Adding tosca standard {} to the CloudShell'.format(standard_name))

        with open(standard_path) as fo:
            self.smb.put_file(self.CS_SHARE, remote_standard_path, fo)

    def get_tosca_standards(self):
        """Get tosca standards from CloudShell.

        :rtype: list[str]"""
        standards = [standard.filename for standard in
                     self.smb.ls(self.CS_SHARE, self.TOSCA_STANDARDS_DIR)]
        self.logger.debug('Installed tosca standards: {}'.format(standards))
        return standards

    def create_reservation(self, name, duration=120):
        """Create reservation

        :param str name: reservation name
        :param int duration: duration of reservation
        :return: reservation id  (uuid)
        :rtype: str
        """

        self.logger.info('Creating the reservation {}'.format(name))
        resp = self.api.CreateImmediateReservation(name, self.api.username, duration)
        id_ = resp.Reservation.Id
        self.logger.debug('Created the reservation id={}'.format(id_))
        return id_

    def create_topology_reservation(
            self, name, topology_name, duration=24*60, specific_version=None):
        """Create topology reservation

        :param str topology_name: Topology Name
        :param str name: reservation name
        :param int duration: duration of reservation
        :param str specific_version:
        :return: reservation id (uuid)
        :rtype: str
        """

        if specific_version:
            global_input_req = [UpdateTopologyGlobalInputsRequest('Version', specific_version)]
        else:
            global_input_req = []

        str_specific_version = ' - {}'.format(specific_version) if specific_version else ''
        self.logger.info('Creating a topology reservation {} for {}{}'.format(
            name, topology_name, str_specific_version))
        resp = self.api.CreateImmediateTopologyReservation(
            name, self.api.username, duration, topologyFullPath=topology_name,
            globalInputs=global_input_req,
        )
        id_ = resp.Reservation.Id
        self.logger.debug('Created a topology reservation id={}'.format(id_))
        return id_

    def create_resource(self, name, family, model, address):
        """Create resource

        :param str name: resource name
        :param str family: resource family, CS_Switch, CS_Firewall, ...
        :param str model: resource model
        :param str address: resource address
        :return: resource name
        :rtype: str
        """

        self.logger.info('Creating the resource {}'.format(name))
        self.logger.debug('Name: {}, family: {}, model: {}, address: {}'.format(
            name, family, model, address))

        while True:
            try:
                self.api.CreateResource(family, model, name, address)
            except CloudShellAPIError as e:
                if str(e.code) != '114':
                    raise

                try:
                    match = re.search(r'^(?P<name>.+)-(?P<v>\d+)$', name)
                    version = int(match.group('v'))
                    name = match.group('name')
                except (AttributeError, KeyError):
                    version = 0

                name = '{}-{}'.format(name, version + 1)

            else:
                break

        self.logger.debug('Created the resource {}'.format(name))

        return name

    def set_resource_attributes(self, resource_name, model, attributes):
        """Set attributes for the resource

        :param str resource_name: resource name
        :param str model: resource model
        :param dict attributes: resource attributes
        """

        self.logger.info('Setting attributes for {}\n{}'.format(resource_name, attributes))

        self.api.SetAttributesValues([
            ResourceAttributesUpdateRequest(resource_name, [
                AttributeNameValue('{}.{}'.format(model, key), value)
                for key, value in attributes.items()
            ])
        ])

    def resource_autoload(self, resource_name):
        """Start autoload for the resource

        :param str resource_name: resource name
        """

        self.logger.info('Start Autoload for the {}'.format(resource_name))
        self.api.AutoLoad(resource_name)
        self.logger.debug('Finished Autoload')

    def update_driver_for_the_resource(self, resource_name, driver_name):
        """Update driver for the resource.

        :type resource_name: str
        :type driver_name: str"""
        self.logger.info('Update Driver "{}" for the Resource "{}"'.format(
            driver_name, resource_name))
        self.api.UpdateResourceDriver(resource_name, driver_name)

    def add_resource_to_reservation(self, reservation_id, resource_name):
        """Adding the resource to the reservation

        :param str reservation_id: reservation id
        :param str resource_name: reservation name
        """

        self.logger.info('Adding a resource {} to a reservation {}'.format(
            resource_name, reservation_id))
        self.api.AddResourcesToReservation(reservation_id, [resource_name])
        self.logger.debug('Added a resource to the reservation')

    def delete_resource(self, resource_name):
        """Delete the resource

        :param str resource_name: resource name
        """

        self.logger.info('Deleting a resource {}'.format(resource_name))
        self.api.DeleteResource(resource_name)
        self.logger.debug('Deleted a resource')

    def delete_reservation(self, reservation_id):
        """Delete the reservation

        :param str reservation_id: reservation id
        """

        self.logger.info('Deleting the reservation {}'.format(reservation_id))
        self.api.DeleteReservation(reservation_id)
        self.logger.debug('Deleted the reservation')

    def end_reservation(self, reservation_id):
        """End the reservation

        :param str reservation_id:
        """

        self.logger.info('Ending a reservation for {}'.format(reservation_id))
        self.api.EndReservation(reservation_id)

    def execute_command_on_resource(
            self, reservation_id, resource_name, command_name, command_kwargs):
        """Execute a command on the resource

        :param str reservation_id: reservation id
        :param str resource_name: resource name
        :param str command_name: command name
        :param dict command_kwargs: command params
        :rtype: str
        """

        self.logger.debug(
            'Executing command {} with kwargs {} for resource {} in reservation {}'.format(
                command_name, command_kwargs, resource_name, reservation_id))
        command_kwargs = [InputNameValue(key, value) for key, value in command_kwargs.items()]
        resp = self.api.ExecuteCommand(
            reservation_id, resource_name, 'Resource', command_name, command_kwargs, True)
        self.logger.debug('Executed command, output {}'.format(resp.Output))
        return resp.Output

    def get_resource_details(self, resource_name):
        """Get resource details

        :param str resource_name: resource name
        :return: resource info
        :rtype: cloudshell.api.cloudshell_api.ResourceInfo
        """

        self.logger.info('Getting resource details for {}'.format(resource_name))
        output = self.api.GetResourceDetails(resource_name)
        self.logger.debug('Got details {}'.format(output))
        return output

    def get_topologies_by_category(self, category_name):
        """Get available topology names by category name

        :param str category_name:
        :return: Topology names
        :rtype: list[str]
        """

        self.logger.info('Getting topologies for a category {}'.format(category_name))
        output = self.api.GetTopologiesByCategory(category_name).Topologies
        self.logger.debug('Got topologies {}'.format(output))
        return output

    def get_reservation_details(self, reservation_id):
        """Get reservation details

        :param str reservation_id:
        :return: reservation details
        :rtype: cloudshell.api.cloudshell_api.GetReservationDescriptionResponseInfo
        """

        self.logger.info('Getting reservation details for the {}'.format(reservation_id))
        output = self.api.GetReservationDetails(reservation_id)
        self.logger.debug('Got reservation details {}'.format(output))
        return output

    def get_reservation_status(self, reservation_id):
        """Check that the reservation ready

        :param str reservation_id: reservation id
        :rtype: cloudshell.api.cloudshell_api.ReservationSlimStatus
        """

        self.logger.debug('Getting reservation status for a {}'.format(reservation_id))
        output = self.api.GetReservationStatus(reservation_id).ReservationSlimStatus
        self.logger.debug('Got status {}'.format(output))
        return output

    def add_file_to_offline_pypi(self, file_obj, file_name):
        """Upload file to offline PyPI

        :param str file_name:
        :param file file_obj:
        """

        excluded = ('.', './', '..', '../')
        if file_name in excluded:
            return

        file_path = os.path.join(self.PYPI_PATH, file_name)
        self.logger.debug('Adding a file {} to offline PyPI'.format(file_path))
        self.smb.put_file(self.CS_SHARE, file_path, file_obj)

    def get_package_names_from_offline_pypi(self):
        """Get package names from offline PyPI"""

        self.logger.debug('Getting packages in offline PyPI')
        excluded = ('.', '..', 'PlaceHolder.txt')
        file_names = [f.filename for f in self.smb.ls(self.CS_SHARE, self.PYPI_PATH)
                      if f.filename not in excluded]
        self.logger.debug('Got packages {}'.format(file_names))
        return file_names

    def remove_file_from_offline_pypi(self, file_name):
        """Remove file from offline PyPI

        :param str file_name:
        """

        file_path = os.path.join(self.PYPI_PATH, file_name)
        self.logger.debug('Removing a file {} from offline PyPI'.format(file_path))
        self.smb.remove_file(self.CS_SHARE, file_path)

    def download_logs(self):
        """Download logs from CloudShell"""

        if os.path.exists(self.CS_LOGS_DIR):
            shutil.rmtree(self.CS_LOGS_DIR)

        os.mkdir(self.CS_LOGS_DIR)

        shell_logs_path = os.path.join(self.CS_LOGS_DIR, 'shell_logs')
        installation_logs_path = os.path.join(self.CS_LOGS_DIR, 'installation_logs')
        os.mkdir(shell_logs_path)
        os.mkdir(installation_logs_path)

        self.smb.download_dir(self.CS_SHARE, self.CS_LOGS_SHELL_DIR, shell_logs_path)
        self.smb.download_dir(self.CS_SHARE, self.CS_LOGS_INSTALLATION_DIR, installation_logs_path)

    def add_physical_connection(self, reservation_id, port1, port2):
        """Add physical connection between two ports

        :param str reservation_id:
        :param str port1: ex, Cisco-IOS-device/Chassis 0/FastEthernet0-1
        :param str port2: ex, Cisco-IOS-device-1/Chassis 0/FastEthernet0-10
        """

        self.logger.info('Create physical connection between {} and {}'.format(port1, port2))
        self.api.UpdatePhysicalConnection(port1, port2)
        self.api.AddRoutesToReservation(reservation_id, [port1], [port2], 'bi')

    def connect_ports_with_connector(self, reservation_id, port1, port2, connector_name):
        """Connect two ports with connector

        :param str reservation_id:
        :param str port1:
        :param str port2:
        :param str connector_name:
        """

        self.logger.info('Creating connector between {} and {}'.format(port1, port2))
        connector = SetConnectorRequest(port1, port2, 'bi', connector_name)
        self.api.SetConnectorsInReservation(reservation_id, [connector])
        self.api.ConnectRoutesInReservation(reservation_id, [port1, port2], 'bi')

    def remove_connector(self, reservation_id, port1, port2):
        """Remove connector between ports

        :param str reservation_id:
        :param str port1:
        :param str port2:
        """

        self.logger.info('Removing connector between {} and {}'.format(port1, port2))
        self.api.DisconnectRoutesInReservation(reservation_id, [port1, port2])
        self.api.RemoveConnectorsFromReservation(reservation_id, [port1, port2])
