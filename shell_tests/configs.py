from collections import OrderedDict
from itertools import chain

import yaml

from shell_tests.errors import BaseAutomationException
from shell_tests.helpers import merge_dicts


class CloudShellConfig(object):
    DEFAULT_DOMAIN = 'Global'

    def __init__(self, host, user, password, os_user=None, os_password=None, domain=None):
        """CloudShell Config.

        :type host: str
        :type user: str
        :type password: str
        :type os_user: str
        :type os_password: str
        :type domain: str
        """
        self.host = host
        self.user = user
        self.password = password
        self.os_user = os_user
        self.os_password = os_password
        self.domain = domain if domain is not None else self.DEFAULT_DOMAIN

    @classmethod
    def from_dict(cls, config):
        if config:
            return cls(
                config['Host'],
                config['User'],
                config['Password'],
                config.get('OS User'),
                config.get('OS Password'),
                config.get('Domain', cls.DEFAULT_DOMAIN),
            )


class DoConfig(CloudShellConfig):
    DEFAULT_CS_VERSION = 'CloudShell 8.3 GA - IL'

    def __init__(self, host, user, password, os_user=None, os_password=None, domain=None,
                 cs_version=DEFAULT_CS_VERSION, delete_cs=True, cs_specific_version=None):

        super(DoConfig, self).__init__(host, user, password, os_user, os_password, domain)
        self.cs_version = cs_version
        self.delete_cs = delete_cs
        self.cs_specific_version = cs_specific_version

    @classmethod
    def from_dict(cls, config):
        if config:
            return cls(
                config['Host'],
                config['User'],
                config['Password'],
                config.get('OS User'),
                config.get('OS Password'),
                config.get('Domain', cls.DEFAULT_DOMAIN),
                config.get('CS Version', cls.DEFAULT_CS_VERSION),
                config.get('Delete CS', 'True') == 'True',
                config.get('CS Specific Version'),
            )


class ResourceConfig(object):
    def __init__(self, name, shell_name, model, device_ip, attributes, children_attributes,
                 tests_conf, first_gen=False):
        """Resource config.

        :type name: str
        :type shell_name: str
        :type model: str
        :type device_ip: str
        :type attributes: dict[str, str]
        :type children_attributes: dict[dict[str, str]]
        :type tests_conf: TestsConfig
        :type first_gen: bool
        """
        self.name = name
        self.shell_name = shell_name
        self.model = model
        self.device_ip = device_ip
        self.attributes = attributes or {}
        self.children_attributes = children_attributes or {}
        self.tests_conf = tests_conf
        self.first_gen = first_gen

        if not shell_name and not model:
            raise BaseAutomationException(
                'You have to specify either shell name or model for the Resource')

    @classmethod
    def from_dict(cls, config):
        if config:
            tests_conf = TestsConfig.from_dict(config.get('Tests'))

            return cls(
                config['Name'],
                config.get('Shell Name'),
                config.get('Model'),
                config.get('Device IP'),
                config.get('Attributes'),
                config.get('Children Attributes'),
                tests_conf,
                config.get('First Gen', False),
            )


class ServiceConfig(object):
    def __init__(self, name, shell_name, model, attributes, tests_conf):
        """Service config.

        :type name: str
        :type shell_name: str
        :type model: str
        :type attributes: dict
        :type tests_conf: TestsConfig
        """
        self.name = name
        self.shell_name = shell_name
        self.model = model
        self.attributes = attributes or {}
        self.tests_conf = tests_conf

        if not shell_name and not model:
            raise BaseAutomationException(
                'You have to specify either shell name or model for the Resource')

    @classmethod
    def from_dict(cls, config):
        if config:
            tests_conf = TestsConfig.from_dict(config.get('Tests'))

            return cls(
                config['Name'],
                config.get('Shell Name'),
                config.get('Model'),
                config.get('Attributes'),
                tests_conf,
            )


class FTPConfig(object):
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password

    @classmethod
    def from_dict(cls, config):
        if config:
            return cls(
                config['Host'],
                config.get('User'),
                config.get('Password'),
            )


class TestsConfig(object):
    def __init__(self, expected_failures, params, run_tests=True):
        """Tests config.

        :type expected_failures: dict[str, str]
        :type params: dict[str, dict[str, str]]
        :param params: {command_name: {param_name: param_value}}
        :type run_tests: bool
        """
        self.expected_failures = expected_failures
        self.params = params
        self.run_tests = run_tests

    @classmethod
    def from_dict(cls, config):
        config = config or {}
        return cls(
            config.get('Expected failures', {}),
            config.get('Params', {}),
            config.get('Run Tests', True),
        )


class ShellConfig(object):
    def __init__(self, name, path, dependencies_path, extra_standards_paths, files_to_store,
                 tests_conf):
        """Shell config.

        :type name: str
        :type path: str
        :type dependencies_path: str
        :type extra_standards_paths: list[str]
        :type files_to_store: dict[str, str]
        :type tests_conf: TestsConfig
        """
        self.name = name
        self.path = path
        self.dependencies_path = dependencies_path
        self.extra_standards_paths = extra_standards_paths
        self.files_to_store = files_to_store
        self.tests_conf = tests_conf

    @classmethod
    def from_dict(cls, config):
        if config:
            tests_conf = TestsConfig.from_dict(config.get('Tests'))

            return cls(
                config['Name'],
                config['Path'],
                config.get('Dependencies Path'),
                config.get('Extra CS Standards', []),
                config.get('Store Files', {}),
                tests_conf,
            )


class SandboxConfig(object):
    def __init__(self, name, resource_names, service_names, blueprint_name):
        """Sandbox config.

        :type name: str
        :type resource_names: list[str]
        :type service_names: list[str]
        :type blueprint_name: str
        """
        self.name = name
        self.resource_names = resource_names
        self.service_names = service_names
        self.blueprint_name = blueprint_name

    @classmethod
    def from_dict(cls, config):
        if config:
            return cls(
                config['Name'],
                config['Resources'],
                config.get('Services', []),
                config.get('Blueprint Name'),
            )


class BlueprintConfig(object):
    def __init__(self, name, path):
        """Blueprint config.

        :type name: str
        :type path: str
        """
        self.name = name
        self.path = path

    @classmethod
    def from_dict(cls, config):
        if config:
            return cls(
                config['Name'],
                config['Path'],
            )


class MainConfig(object):
    def __init__(self, do_conf, cs_conf, shells_conf, resources_conf, services_conf, sandboxes_conf,
                 ftp_conf, blueprints_conf):
        """Main config.

        :type do_conf: DoConfig
        :type cs_conf: CloudShellConfig
        :type shells_conf: OrderedDict[str, ShellConfig]
        :type resources_conf: OrderedDict[str, ResourceConfig]
        :type services_conf: OrderedDict[str, ServiceConfig]
        :type sandboxes_conf: OrderedDict[str, SandboxConfig]
        :type ftp_conf: FTPConfig
        :type blueprints_conf: OrderedDict[str, BlueprintConfig]
        """
        self.do_conf = do_conf
        self.cs_conf = cs_conf
        self.shells_conf = shells_conf
        self.resources_conf = resources_conf
        self.services_conf = services_conf
        self.sandboxes_conf = sandboxes_conf
        self.ftp_conf = ftp_conf
        self.blueprints_conf = blueprints_conf

    @classmethod
    def parse_from_yaml(cls, test_conf_path, env_conf_path=None):
        env_conf = {}
        if env_conf_path is not None:
            with open(env_conf_path) as fo:
                env_conf = yaml.safe_load(fo.read())

        with open(test_conf_path) as fo:
            test_conf = yaml.safe_load(fo.read())

        config = merge_dicts(test_conf, env_conf)
        cls._update_resource_tests_conf(config)

        do_conf = DoConfig.from_dict(config.get('Do'))
        cs_conf = CloudShellConfig.from_dict(config.get('CloudShell'))

        shells_conf = OrderedDict(
            (shell_conf['Name'], ShellConfig.from_dict(shell_conf))
            for shell_conf in config['Shells']
        )
        resources_conf = OrderedDict(
            (resource_conf['Name'], ResourceConfig.from_dict(resource_conf))
            for resource_conf in config['Resources']
        )
        services_conf = OrderedDict(
            (service_conf['Name'], ServiceConfig.from_dict(service_conf))
            for service_conf in config.get('Services', [])
        )
        sandboxes_conf = OrderedDict(
            (sandbox_conf['Name'], SandboxConfig.from_dict(sandbox_conf))
            for sandbox_conf in config['Sandboxes']
        )
        ftp_conf = FTPConfig.from_dict(config.get('FTP'))
        blueprints_conf = OrderedDict(
            (blueprint_conf['Name'], BlueprintConfig.from_dict(blueprint_conf))
            for blueprint_conf in config.get('Blueprints', [])
        )

        return cls(
            do_conf,
            cs_conf,
            shells_conf,
            resources_conf,
            services_conf,
            sandboxes_conf,
            ftp_conf,
            blueprints_conf,
        )

    @staticmethod
    def _update_resource_tests_conf(conf):
        for resource_dict in chain(conf.get('Resources', []), conf.get('Services', [])):
            for shell_dict in conf['Shells']:
                if shell_dict['Name'] == resource_dict.get('Shell Name'):
                    resource_dict['Tests'] = merge_dicts(
                        resource_dict.get('Tests', {}),
                        shell_dict.get('Tests', {}))
                    break
