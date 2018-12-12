from cs_handler import CloudShellHandler
from shell_tests.helpers import get_resource_family_and_model


class ResourceHandler(object):
    RESERVATION_NAME = 'automation_tests'
    REAL_DEVICE = 'Real device'
    SIMULATOR = 'Simulator'
    WITHOUT_DEVICE = 'Without device'

    def __init__(
            self, cs_handler, device_ip, resource_name, shell_path, logger,
            reservation_name=RESERVATION_NAME):
        """Handler for install shell and test it

        :param CloudShellHandler cs_handler: CloudShell Handler
        :param str device_ip: device IP
        :param str shell_path:
        :param logging.Logger logger:
        :param str reservation_name: Reservation name
        """

        self.cs_handler = cs_handler
        self.device_ip = device_ip
        self.resource_name = resource_name
        self.shell_path = shell_path
        self.logger = logger
        self.reservation_name = reservation_name

        self.resource_family, self.resource_model = get_resource_family_and_model(
            self.shell_path, self.logger)
        self.attributes = {}
        self.reservation_id = None

    @property
    def device_type(self):
        if not self.device_ip:
            return self.WITHOUT_DEVICE
        elif self.attributes.get('User'):
            return self.REAL_DEVICE
        else:
            return self.SIMULATOR

    def prepare_resource(self):
        """Prepare the Resource.

        Create a reservation, create a resource and add the resource to the reservation
        """
        self.logger.info('Start preparing the resource {}'.format(self.resource_name))

        self.reservation_id = self.cs_handler.create_reservation(self.reservation_name)
        self.resource_name = self.cs_handler.create_resource(
            self.resource_name,
            self.resource_family,
            self.resource_model,
            self.device_ip or '127.0.0.1',  # if we don't have a real device
        )
        self.cs_handler.add_resource_to_reservation(self.reservation_id, self.resource_name)

        self.logger.info('The resource {} prepared'.format(self.resource_name))

    def delete_resource(self):
        """Delete reservation and resource."""
        self.logger.info('Start deleting the resource {}'.format(self.resource_name))

        self.cs_handler.delete_reservation(self.reservation_id)
        self.cs_handler.delete_resource(self.resource_name)

        self.logger.info('The resource {} deleted'.format(self.resource_name))

    def __enter__(self):
        self.prepare_resource()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delete_resource()
        return False

    def set_attributes(self, attributes):
        """Set attributes for the resource and update internal dict"""

        self.cs_handler.set_resource_attributes(self.resource_name, self.resource_model, attributes)
        self.attributes.update(attributes)

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

    def save(self, ftp_path, configuration_type):
        """Execute save command on the resource"""

        self.logger.info('Start a "save" command')
        self.logger.debug(
            'FTP path: {}, configuration type: {}'.format(ftp_path, configuration_type))

        output = self.execute_command(
            'save',
            {'folder_path': ftp_path, 'configuration_type': configuration_type}
        )
        self.logger.debug('Save command output: {}'.format(output))
        return output

    def orchestration_save(self, mode, custom_params=''):
        """Execute orchestration save command

        :param str mode: shallow or deep
        :param str custom_params:
        """

        self.logger.info('Start a "orchestration save" command')
        self.logger.debug('Mode: {}, custom params: {}'.format(mode, custom_params))

        output = self.execute_command(
            'orchestration_save',
            {'mode': mode, 'custom_params': custom_params},
        )

        self.logger.debug('Orchestration save command output: {}'.format(output))
        return output

    def restore(self, path, configuration_type, restore_method):
        """Execute restore command

        :param str path: path to the file
        :param str configuration_type: startup or running
        :param str restore_method: append or override
        """

        self.logger.info('Start a "restore" command')
        self.logger.debug(
            'Path: {}, configuration_type: {}, restore_method: {}'.format(
                path, configuration_type, restore_method)
        )

        output = self.execute_command(
            'restore',
            {'path': path, 'configuration_type': configuration_type,
             'restore_method': restore_method}
        )

        self.logger.debug('Restore command output: {}'.format(output))
        return output

    def orchestration_restore(self, saved_artifact_info, custom_params=''):
        """Execute orchestration restore command

        :param str saved_artifact_info:
        :param str custom_params:
        """

        self.logger.info('Start a "orchestration restore" command')
        self.logger.debug(
            'Saved artifact info: {}, custom params: {}'.format(saved_artifact_info, custom_params))

        output = self.execute_command(
            'orchestration_restore',
            {'saved_artifact_info': saved_artifact_info, 'custom_params': custom_params},
        )

        self.logger.debug('Orchestration restore command output: {}'.format(output))
        return output
