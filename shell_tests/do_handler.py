import time

from shell_tests.errors import BaseAutomationException, CSIsNotAliveError


class DoHandler(object):
    RESERVATION_NAME = 'automation_tests'
    DEFAULT_USER = 'admin'
    DEFAULT_PASSWORD = 'admin'

    def __init__(self, cs_handler, logger, reservation_name=RESERVATION_NAME):
        """Handler for creating CloudShell instance on DO

        :param src.cs_handler.CloudShellHandler cs_handler: CloudShell Handler
        :param logging.Logger logger:
        :param str reservation_name: CloudShell reservation name
        """

        self.cs_handler = cs_handler
        self.logger = logger
        self.reservation_name = reservation_name

        self.reservation_id = None
        self.resource_name = None
        self.cs_ip = None
        self.cs_user = self.DEFAULT_USER
        self.cs_password = self.DEFAULT_PASSWORD
        self.cs_os_user = None
        self.cs_os_password = None

    def start_cloudshell(self, version, cs_specific_version=None):
        """Execute a command for starting CloudShell

        :param str version: version of CS
        :param str cs_specific_version:
        """

        cs_names = sorted(self.cs_handler.get_topologies_by_category('CloudShell'))

        for cs_name in cs_names:
            if cs_name.split('/')[-1] == version:  # 'Environments/CloudShell - Latest 8.3'
                break
        else:
            raise BaseAutomationException('CloudShell version {} isn\'t correct'.format(version))

        self.logger.debug('Creating CloudShell {}'.format(cs_name))

        self.reservation_id = self.cs_handler.create_topology_reservation(
            self.reservation_name, cs_name, specific_version=cs_specific_version)

    def _get_resource_name(self):
        """Get CloudShell resource name"""
        for _ in range(10*6):
            info = self.cs_handler.get_reservation_details(self.reservation_id)
            if info.ReservationDescription.Resources:
                break
            time.sleep(10)
        else:
            raise BaseAutomationException('Could not create CloudShell instance')

        return info.ReservationDescription.Resources[0].Name

    def get_new_cloudshell(self, version, cs_specific_version=None):
        """Start CloudShell and wait for starting it"""

        self.logger.info('Start creating CloudShell with version {}'.format(version))
        try:
            self.start_cloudshell(version, cs_specific_version)
        except BaseAutomationException:
            raise BaseAutomationException('CloudShell isn\'t started')

        self.resource_name = self._get_resource_name()

        for _ in range(10 * 60):
            resource_info = self.cs_handler.get_resource_details(self.resource_name)
            self.cs_ip = resource_info.FullAddress
            if self.cs_ip != 'NA':
                break
            time.sleep(10)
        else:
            raise CSIsNotAliveError

        for attr in resource_info.ResourceAttributes:
            if attr.Name == 'OS Login':
                self.cs_os_user = attr.Value
            elif attr.Name == 'OS Password':
                self.cs_os_password = attr.Value
            if self.cs_os_user and self.cs_os_password:
                break

        self.logger.info('CloudShell created IP: {}'.format(self.cs_ip))
        self.logger.debug('IP: {}, User: {}, Password: {}, OS User: {}, OS Password: {}'.format(
            self.cs_ip, self.cs_user, self.cs_password, self.cs_os_user, self.cs_os_password))

        return self.cs_ip, self.cs_user, self.cs_password, self.cs_os_user, self.cs_os_password

    def end_reservation(self):
        """End CloudShell reservation."""
        self.cs_handler.end_reservation(self.reservation_id)
