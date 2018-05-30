import os
import urlparse
import zipfile

import requests
import yaml

from src.cs_handler import CloudShellHandler


class ResourceHandler(object):
    RESERVATION_NAME = 'automation_tests'
    DOWNLOAD_FOLDER = 'downloads'

    def __init__(
            self, cs_handler, shell_path, dependencies_path, device_ip, resource_name, logger,
            reservation_name=RESERVATION_NAME):
        """Handler for install shell and test it

        :param CloudShellHandler cs_handler: CloudShell Handler
        :param str shell_path: path to zip file
        :param str dependencies_path: path to zip file
        :param str device_ip: device IP
        :param logging.Logger logger:
        :param str reservation_name: Reservation name
        """

        self.cs_handler = cs_handler
        self.shell_path = shell_path
        self.dependencies_path = dependencies_path
        self.device_ip = device_ip
        self.resource_name = resource_name
        self.logger = logger
        self.reservation_name = reservation_name

        self.reservation_id = None
        self._resource_family = None
        self._resource_model = None
        self.dependencies_file = None
        self.shell_file = None
        self._download_folder = None

    def _get_resource_family_and_model(self):
        """Get resource family and model from shell-definition.yaml

        :return: family and model
        :rtype: tuple[str, str]"""

        zip_file = zipfile.ZipFile(self.shell_path)
        data = yaml.load(zip_file.read('shell-definition.yaml'))

        model = data['node_types'].keys()[0].rsplit('.', 1)[-1]
        family = data['node_types'].values()[0]['derived_from'].rsplit('.', 1)[-1]
        family = 'CS_{}'.format(family)  # todo get it from standard
        self.logger.debug('Family: {}, model: {} for the Shell {}'.format(
            family, model, self.shell_path))
        return family, model

    @property
    def download_folder(self):
        if not self._download_folder:
            path = os.path.abspath(
                os.path.join(__file__, '../../{}'.format(self.DOWNLOAD_FOLDER)))
            if not os.path.exists(path):
                os.mkdir(path)
            self._download_folder = path

        return self._download_folder

    def download_file(self, url):
        """Download file to tmp folder"""

        file_name = url.rsplit('/', 1)[-1]

        resp = requests.get(url)
        file_path = os.path.join(self.download_folder, file_name)
        with open(file_path, 'w') as file_obj:
            file_obj.write(resp.content)

        return file_path, file_obj

    @staticmethod
    def is_url(url):
        return urlparse.urlparse(url).scheme != ''

    @property
    def resource_family(self):
        if self._resource_family is None:
            self._resource_family, self._resource_model = self._get_resource_family_and_model()
        return self._resource_family

    @property
    def resource_model(self):
        if self._resource_model is None:
            self._resource_family, self._resource_model = self._get_resource_family_and_model()
        return self._resource_model

    def install_shell(self):
        """Install the Shell"""

        if self.is_url(self.shell_path):
            self.logger.info('Downloading the Shell from {}'.format(self.shell_path))
            self.shell_path, self.shell_file = self.download_file(self.shell_path)
        self.cs_handler.install_shell(self.shell_path)

    def prepare_resource(self):
        """Prepare Shell and Resource

        Adding dependencies if needed ,install the Shell to the CloudShell, create a reservation,
        create a resource and add the resource to the reservation
        """

        self.logger.info('Start preparing the resource {}'.format(self.resource_name))

        if self.dependencies_path:
            self.add_dependencies_to_offline_pypi()

        self.install_shell()
        self.reservation_id = self.cs_handler.create_reservation(self.reservation_name)
        self.resource_name = self.cs_handler.create_resource(
            self.resource_name, self.resource_family, self.resource_model, self.device_ip)
        self.cs_handler.add_resource_to_reservation(self.reservation_id, self.resource_name)

        self.logger.info('The resource {} prepared'.format(self.resource_name))

    def delete_resource(self):
        """Delete reservation and resource"""

        self.logger.info('Start deleting the resource {}'.format(self.resource_name))

        if self.dependencies_path:
            self.clear_offline_pypi()

        self.deleting_downloaded_shell()

        self.cs_handler.delete_reservation(self.reservation_id)
        self.cs_handler.delete_resource(self.resource_name)

        self.logger.info('The resource {} deleted'.format(self.resource_name))

    def __enter__(self):
        self.prepare_resource()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delete_resource()
        return False

    def add_dependencies_to_offline_pypi(self):
        """Upload all dependencies from zip file to offline PyPI"""

        self.logger.info('Putting dependencies to offline PyPI')

        if self.is_url(self.dependencies_path):
            self.logger.info('Downloading the dependencies file from {}'.format(
                self.dependencies_path))
            self.dependencies_path, self.dependencies_file = self.download_file(
                self.dependencies_path)

        zip_file = zipfile.ZipFile(self.dependencies_path)
        for file_obj in map(zip_file.open, zip_file.filelist):
            self.cs_handler.add_file_to_offline_pypi(file_obj, file_obj.name)

    def clear_offline_pypi(self):
        """Delete all packages from offline PyPI"""

        self.logger.info('Clearing offline PyPI')
        for file_name in self.cs_handler.get_package_names_from_offline_pypi():
            self.cs_handler.remove_file_from_offline_pypi(file_name)

    def deleting_downloaded_shell(self):
        """Delete downloaded Shell and dependencies if downloaded"""

        if self.shell_file:
            self.logger.debug('Delete a downloaded Shell file')
            os.remove(self.shell_path)
        if self.dependencies_file:
            self.logger.debug('Delete a downloaded dependenies file')
            os.remove(self.dependencies_path)

    def set_attributes(self, attributes):
        """Set attributes for the resource"""

        self.cs_handler.set_resource_attributes(self.resource_name, self.resource_model, attributes)

    def autoload(self):
        """Run Autoload for the resource"""

        return self.cs_handler.resource_autoload(self.resource_name)

    def get_details(self):
        """Get resource details"""

        return self.cs_handler.get_resource_details(self.resource_name)

    def execute_command(self, command_name, command_kwargs):
        """Execute a command for the resource

        :param str command_name: a command to run
        :param dict command_kwargs: command params
        """

        return self.cs_handler.execute_command_on_resource(
            self.reservation_id, self.resource_name, command_name, command_kwargs)

    def health_check(self):
        """Run health check command on the resource"""

        self.logger.info('Starting a "health_check" command for the {}'.format(self.resource_name))
        output = self.execute_command('health_check', {})
        self.logger.debug('Health check output: {}'.format(output))
        return output

    def run_custom_command(self, command):
        """Execute run custom command on the resource"""

        self.logger.info('Start a "run_custom_command" command {}'.format(command))
        output = self.execute_command('run_custom_command', {'custom_command': command})
        self.logger.debug('Run custom command output: {}'.format(output))
        return output

    def run_custom_config_command(self, command):
        """Execute run custom config command on the resource"""

        self.logger.info('Start a "run_custom_config_command" command {}'.format(command))
        output = self.execute_command('run_custom_config_command', {'custom_command': command})
        self.logger.debug('Run custom config command output: {}'.format(output))
        return output
