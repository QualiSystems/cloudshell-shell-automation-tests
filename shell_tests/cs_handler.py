import base64
import os
import re
import shutil
import time

import requests
from cloudshell.api.cloudshell_api import CloudShellAPISession, ResourceAttributesUpdateRequest, \
    AttributeNameValue, InputNameValue, SetConnectorRequest, UpdateTopologyGlobalInputsRequest
from cloudshell.api.common_cloudshell_api import CloudShellAPIError
from cloudshell.rest.api import PackagingRestApiClient
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

from shell_tests.errors import BaseAutomationException, CreationReservationError
from shell_tests.helpers import cached_property
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

    @cached_property
    def rest_api(self):
        self.logger.debug('Connecting to REST API')
        rest_api = PackagingRestApiClient(self.host, self.REST_API_PORT, self.user, self.password, self.domain)
        self.logger.debug('Connected to REST API')
        return rest_api

    @cached_property
    def api(self):
        self.logger.debug('Connecting to Automation API')
        api = CloudShellAPISession(self.host, self.user, self.password, self.domain)
        self.logger.debug('Connected to Automation API')
        return api

    @cached_property
    def smb(self):
        if self.os_user:
            smb = SMB(
                self.os_user,
                self.os_password,
                self.host,
                self.CLOUDSHELL_SERVER_NAME,
                self.logger,
            )
            return smb

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

    def import_package(self, package_path):
        """Import the package to the CloudShell.

        :type package_path: str
        """
        self.logger.info('Importing a package {} to the CloudShell'.format(package_path))
        self.rest_api.import_package(package_path)
        self.logger.debug('Imported the package')

    def add_cs_standard(self, standard_path):
        """Put standard into tosca standards' dir.

        :type standard_path: str
        """
        standard_name = os.path.basename(standard_path)
        remote_standard_path = os.path.join(self.TOSCA_STANDARDS_DIR, standard_name)

        self.logger.warning('Adding a tosca standard {} to the CloudShell'.format(standard_name))
        self.store_file(remote_standard_path, src_path=standard_path)

    def store_file(self, dst_path, src_path=None, src_obj=None, force=False):
        """Store the src file to the dst on the CS.

        :type dst_path: str
        :type src_path: str
        :type src_obj: file
        :type force: bool
        """
        if not src_obj:
            src_obj = open(src_path, 'rb')

        try:
            return self.smb.put_file(self.CS_SHARE, dst_path, src_obj, force)
        finally:
            if src_path:
                src_obj.close()

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
        :param bool wait: wait for reservation is started
        :return: reservation id  (uuid)
        :rtype: str
        """
        self.logger.info('Creating the reservation {}'.format(name))
        resp = self.api.CreateImmediateReservation(name, self.api.username, duration)
        return resp.Reservation.Id

    def create_topology_reservation(self, name, topology_name, duration=24*60, specific_version=None):
        """Create topology reservation

        :param str topology_name: Topology Name
        :param str name: reservation name
        :param int duration: duration of reservation
        :param str specific_version:
        :param bool wait: wait for reservation is started
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
        return resp.Reservation.Id

    def wait_reservation_is_started(self, reservation_id):
        for _ in range(60):
            status = self.get_reservation_status(reservation_id)
            if (
                    status.ProvisioningStatus == 'Ready'
                    or status.ProvisioningStatus == 'Not Run' and status.Status == 'Started'
            ):
                break
            elif status.ProvisioningStatus == 'Error':
                errors = list(self.get_reservation_errors(reservation_id))
                self.logger.error('Reservation {} started with errors: {}'.format(reservation_id, errors))
                raise CreationReservationError(errors)

            time.sleep(30)
        else:
            raise CreationReservationError('The reservation {} doesn\'t started'.format(reservation_id))
        self.logger.info('The reservation created')

    def get_reservation_errors(self, reservation_id):
        """Get error messages from activity tab in reservation."""
        login_url = 'http://{}/Account/Login'.format(self.host)
        get_activities_url = 'http://{}/api/WorkspaceApi/GetFilteredActivityFeedInfoList?diagramId={}'.format(
            self.host, reservation_id)
        public_key_url = 'http://{}/Account/PublicKey'.format(self.host)
        get_activity_url = 'http://{}/api/WorkspaceApi/GetActivityFeedInfo?eventId='.format(self.host)

        data = {
            'FromEventId': 0,
            'IsError': True,
        }

        with requests.session() as session:
            resp = session.get(public_key_url)  # download public key
            public_key = serialization.load_pem_public_key(resp.content, default_backend())

            username = public_key.encrypt(self.user, padding.PKCS1v15())
            username = base64.b64encode(username)
            password = public_key.encrypt(self.password, padding.PKCS1v15())
            password = base64.b64encode(password)

            session.post(login_url, data={'username': username, 'password': password})
            resp = session.post(get_activities_url, data=data)

            for id_ in [item['Id'] for item in resp.json()['Data']['Items']]:
                url = get_activity_url + str(id_)
                resp = session.get(url)
                data = resp.json()['Data']
                text = data['Text']
                output = data['Output']

                yield text, output

    @staticmethod
    def create_new_resource_name(name):
        """Create new name with index.

        :type name: str
        :rtype: str
        """
        try:
            match = re.search(r'^(?P<name>.+)-(?P<v>\d+)$', name)
            version = int(match.group('v'))
            name = match.group('name')
        except (AttributeError, KeyError):
            version = 0

        return '{}-{}'.format(name, version + 1)

    def create_resource(self, name, model, address, family=''):
        """Create resource.

        :param str name: resource name
        :param str model: resource model
        :param str address: resource address
        :param str family: resource family, CS_Switch, CS_Firewall, ... (Optional)
        :return: resource name
        :rtype: str
        """
        self.logger.info('Creating the resource {}'.format(name))
        self.logger.debug('Name: {}, model: {}, address: {}'.format(name, model, address))

        while True:
            try:
                self.api.CreateResource(family, model, name, address)
            except CloudShellAPIError as e:
                if str(e.code) != '114':
                    raise
                name = self.create_new_resource_name(name)
            else:
                break

        self.logger.debug('Created the resource {}'.format(name))

        return name

    def rename_resource(self, current_name, new_name):
        """Rename resource.

        :type current_name: str
        :type new_name: str
        :rtype: str
        """
        self.logger.info('Renaming resource "{}" to "{}"'.format(current_name, new_name))

        while True:
            try:
                self.api.RenameResource(current_name, new_name)
            except CloudShellAPIError as e:
                if str(e.code) != '114':
                    raise
                new_name = self.create_new_resource_name(new_name)
            else:
                break

        self.logger.debug('Resource "{}" renamed to "{}"'.format(current_name, new_name))
        return new_name

    def set_resource_attributes(self, resource_name, namespace, attributes):
        """Set attributes for the resource.

        :param str resource_name: resource name
        :param str namespace: name space
        :param dict attributes: resource attributes
        """
        self.logger.info('Setting attributes for {}\n{}'.format(resource_name, attributes))

        namespace += '.' if namespace else ''
        self.api.SetAttributesValues([
            ResourceAttributesUpdateRequest(resource_name, [
                AttributeNameValue('{}{}'.format(namespace, key), value)
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

    def add_service_to_reservation(self, reservation_id, service_model, service_name, attributes):
        """Add the service to the reservation.

        :type reservation_id: str
        :type service_model: str
        :type service_name: str
        :type attributes: dict
        """
        self.logger.info('Adding a service {} to a reservation {}'.format(
            service_name, reservation_id))

        attributes = [
            AttributeNameValue('{}.{}'.format(service_model, key), value)
            for key, value in attributes.items()
        ]
        self.api.AddServiceToReservation(
            reservation_id, service_model, service_name, attributes)

        self.logger.debug('Added the service to the reservation')

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

    def end_reservation(self, reservation_id, wait=True):
        """End the reservation.

        :type reservation_id: str
        :type wait: bool
        """
        self.logger.info('Ending a reservation for {}'.format(reservation_id))
        self.api.EndReservation(reservation_id)

        if wait:
            for _ in range(30):
                status = self.get_reservation_status(reservation_id).Status
                if status == 'Completed':
                    break
                time.sleep(30)
            else:
                raise BaseAutomationException('Can\'t end reservation')
            self.logger.info('Reservation ended')

    def _execute_command(self, reservation_id, target_name, target_type, command_name,
                         command_kwargs):
        """Execute a command on the target.

        :type reservation_id: str
        :type target_name: str
        :type target_type: str
        :param target_type: Resource or Service
        :type command_name: str
        :type command_kwargs: dict[str, str]
        :rtype: str
        """
        self.logger.debug(
            'Executing command {} with kwargs {} for the target {} in the reservation {}'.format(
                command_name, command_kwargs, target_name, reservation_id))
        command_kwargs = [InputNameValue(key, value) for key, value in command_kwargs.items()]
        resp = self.api.ExecuteCommand(
            reservation_id, target_name, target_type, command_name, command_kwargs, True)
        self.logger.debug('Executed command, output {}'.format(resp.Output))
        return resp.Output

    def execute_command_on_resource(
            self, reservation_id, resource_name, command_name, command_kwargs):
        """Execute a command on the resource.

        :param str reservation_id: reservation id
        :param str resource_name: resource name
        :param str command_name: command name
        :param dict command_kwargs: command params
        :rtype: str
        """
        return self._execute_command(
            reservation_id, resource_name, 'Resource', command_name, command_kwargs)

    def execute_command_on_service(
            self, reservation_id, service_name, command_name, command_kwargs):
        return self._execute_command(
            reservation_id, service_name, 'Service', command_name, command_kwargs)

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
        self.logger.debug('Got topologies {}'.format(sorted(output)))
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
        self.store_file(file_path, src_obj=file_obj)

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

    def get_resources_names_in_reservation(self, reservation_id):
        """Get resources names in the reservation.

        :type reservation_id: str
        :rtype: list[str]
        """
        self.logger.info('Get resources names in the reservation {}'.format(reservation_id))
        resources_info = self.api.GetReservationResourcesPositions(
            reservation_id).ResourceDiagramLayouts
        names = [resource.ResourceName for resource in resources_info]
        self.logger.info('Resources names are: {}'.format(names))
        return names

    def refresh_vm_details(self, reservation_id, app_names):
        """Refresh VM Details.

        :type reservation_id: str
        :type app_names: list[str]
        """
        self.logger.info('Refresh VM Details for the "{}"'.format(app_names))
        self.api.RefreshVMDetails(reservation_id, app_names)
        self.logger.debug('VM Details are refreshed')
