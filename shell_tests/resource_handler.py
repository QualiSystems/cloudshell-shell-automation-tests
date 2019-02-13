from cloudshell.api.common_cloudshell_api import CloudShellAPIError


class DeviceType(object):
    REAL_DEVICE = 'Real device'
    SIMULATOR = 'Simulator'
    WITHOUT_DEVICE = 'Without device'


class ResourceHandler(object):
    RESERVATION_NAME = 'automation_tests'

    def __init__(self, name, device_ip, attributes, tests_conf, cs_handler, sandbox_handler,
                 shell_handler, logger):
        """Handler for install shell and test it.

        :type name: str
        :type device_ip: str
        :type attributes: dict[str, str]
        :type tests_conf: shell_tests.configs.TestsConfig
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type sandbox_handler: shell_tests.sandbox_handler.SandboxHandler
        :type shell_handler: shell_tests.shell_handler.ShellHandler
        :type logger: logging.Logger
        """
        self.name = name
        self.device_ip = device_ip
        self.tests_conf = tests_conf
        self.cs_handler = cs_handler
        self.sandbox_handler = sandbox_handler
        self.shell_handler = shell_handler
        self.logger = logger
        self.model, self.family = shell_handler.model, shell_handler.family

        self.attributes = {}
        self._initial_attributes = attributes or {}

    @classmethod
    def from_conf(cls, conf, cs_handler, sandbox_handler, shell_handler, logger):
        """Create Resource Handler from the config and handlers.

        :type conf: shell_tests.configs.ResourceConfig
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type sandbox_handler: shell_tests.sandbox_handler.SandboxHandler
        :type shell_handler: shell_tests.shell_handler.ShellHandler
        :type logger: logging.Logger
        """
        return cls(
            conf.name,
            conf.device_ip,
            conf.attributes,
            conf.tests_conf,
            cs_handler,
            sandbox_handler,
            shell_handler,
            logger,
        )

    @property
    def device_type(self):
        if not self.device_ip:
            return DeviceType.WITHOUT_DEVICE
        elif self.attributes.get('User'):
            return DeviceType.REAL_DEVICE
        else:
            return DeviceType.SIMULATOR

    def prepare_resource(self):
        """Prepare the Resource.

        Create create the resource and add the resource to the reservation
        """
        self.logger.info('Start preparing the resource {}'.format(self.name))

        self.name = self.cs_handler.create_resource(
            self.name,
            self.family,
            self.model,
            self.device_ip or '127.0.0.1',  # if we don't have a real device
        )
        self.set_attributes(self._initial_attributes)

        self.logger.info('The resource {} prepared'.format(self.name))

    def delete_resource(self):
        """Delete reservation and resource."""
        self.logger.info('Start deleting the resource {}'.format(self.name))

        self.cs_handler.delete_resource(self.name)

        self.logger.info('The resource {} deleted'.format(self.name))

    def __enter__(self):
        self.prepare_resource()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delete_resource()
        return False

    def set_attributes(self, attributes):
        """Set attributes for the resource and update internal dict.

        :type attributes: dict[str, str]
        """
        if attributes:
            self.cs_handler.set_resource_attributes(self.name, self.model, attributes)
            self.attributes.update(attributes)

    def autoload(self):
        """Run Autoload for the resource."""
        try:
            result = self.cs_handler.resource_autoload(self.name)
        except CloudShellAPIError as e:
            if str(e.code) != '129' and e.message != 'no driver associated':
                raise

            self.cs_handler.update_driver_for_the_resource(self.name, self.model)
            result = self.cs_handler.resource_autoload(self.name)

        return result

    def get_details(self):
        """Get resource details"""

        return self.cs_handler.get_resource_details(self.name)

    def execute_command(self, command_name, command_kwargs):
        """Execute the command for the resource.

        :type command_name: str
        :type command_kwargs: dict
        """
        return self.sandbox_handler.execute_resource_command(
            self.name, command_name, command_kwargs)

    def health_check(self):
        """Run health check command on the resource."""
        self.logger.info('Starting a "health_check" command for the {}'.format(self.name))
        output = self.execute_command('health_check', {})
        self.logger.debug('Health check output: {}'.format(output))
        return output

    def run_custom_command(self, command):
        """Execute run custom command on the resource."""
        self.logger.info('Start a "run_custom_command" command {}'.format(command))
        output = self.execute_command('run_custom_command', {'custom_command': command})
        self.logger.debug('Run custom command output: {}'.format(output))
        return output

    def run_custom_config_command(self, command):
        """Execute run custom config command on the resource."""
        self.logger.info('Start a "run_custom_config_command" command {}'.format(command))
        output = self.execute_command('run_custom_config_command', {'custom_command': command})
        self.logger.debug('Run custom config command output: {}'.format(output))
        return output

    def save(self, ftp_path, configuration_type):
        """Execute save command on the resource."""
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
        """Execute orchestration save command.

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
        """Execute restore command.

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
        """Execute orchestration restore command.

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


class ServiceHandler(object):

    def __init__(self, name, attributes, tests_conf, cs_handler, sandbox_handler, shell_handler,
                 logger):
        """Handler for the Service.

        :type name: str
        :type attributes: dict[str, str]
        :type tests_conf: shell_tests.configs.TestsConfig
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type sandbox_handler: shell_tests.sandbox_handler.SandboxHandler
        :type shell_handler: shell_tests.shell_handler.ShellHandler
        :type logger: logging.Logger
        """
        self.name = name
        self.tests_conf = tests_conf
        self.cs_handler = cs_handler
        self.sandbox_handler = sandbox_handler
        self.shell_handler = shell_handler
        self.logger = logger
        self.model, self.family = shell_handler.model, shell_handler.family
        self.attributes = attributes

        self._related_resource_handler = None

    @classmethod
    def from_conf(cls, conf, cs_handler, sandbox_handler, shell_handler, logger):
        """Create Resource Handler from the config and handlers.

        :type conf: shell_tests.configs.ServiceConfig
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type sandbox_handler: shell_tests.sandbox_handler.SandboxHandler
        :type shell_handler: shell_tests.shell_handler.ShellHandler
        :type logger: logging.Logger
        """
        return cls(
            conf.name,
            conf.attributes,
            conf.tests_conf,
            cs_handler,
            sandbox_handler,
            shell_handler,
            logger,
        )

    @property
    def device_type(self):
        if self.related_resource_handler:
            return self.related_resource_handler.device_type

        return DeviceType.REAL_DEVICE

    @property
    def related_resource_handler(self):
        if self._related_resource_handler is False:
            return

        if self._related_resource_handler is None:
            self._related_resource_handler = self.sandbox_handler.resource_handlers[0]

        return self._related_resource_handler

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute_command(self, command_name, command_kwargs):
        """Execute the command for the service.

        :type command_name: str
        :type command_kwargs: dict[str, str]
        """
        return self.sandbox_handler.execute_service_command(self.name, command_name, command_kwargs)

    def load_config(self, config_path, use_ports_from_res=False):
        """Execute a command load_config for the service.

        :type config_path: str
        :type use_ports_from_res: bool
        """
        return self.execute_command(
            'load_config', {
                'config_file_location': config_path,
                'use_ports_from_reservation': use_ports_from_res,
            },
        )

    def start_traffic(self):
        """Execute a command start traffic for the service."""
        return self.execute_command('start_traffic', {})

    def stop_traffic(self):
        """Execute a command stop traffic for the service."""
        return self.execute_command('stop_traffic', {})

    def get_statistics(self):
        """Execute a command get statistics for the service."""
        return self.execute_command('get_statistics', {})
