import re

import yaml


class CloudShellConfig(object):
    DEFAULT_DOMAIN = 'Global'

    def __init__(self, host, user, password, os_user=None, os_password=None, domain=DEFAULT_DOMAIN):
        self.host = host
        self.user = user
        self.password = password
        self.os_user = os_user
        self.os_password = os_password
        self.domain = domain

    @classmethod
    def from_dict(cls, config):
        if config:
            return cls(
                config['Host'],
                config['User'],
                config['Password'],
                config.get('OS User'),
                config.get('OS Password'),
                config.get('Domain', CloudShellConfig.DEFAULT_DOMAIN),
            )


class ResourceConfig(object):
    def __init__(self, resource_name, device_ip, attributes):
        """Resource config

        :param str resource_name:
        :param str device_ip:
        :param dict attributes:
        """

        self.resource_name = resource_name
        self.device_ip = device_ip
        self.attributes = attributes

    @classmethod
    def from_dict(cls, config):
        if config:
            return cls(
                config['Name'],
                config.get('Device IP'),
                config.get('Attributes'),
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
                config['User'],
                config['Password'],
            )


class TestsConfig(object):
    def __init__(self, expected_failures):
        """Tests config

        :param dict expected_failures:
        """

        self.expected_failures = expected_failures

    @classmethod
    def from_dict(cls, config):
        if config:
            return cls(
                config['Expected failures'],
            )


class ShellConfig(object):
    def __init__(
            self, do_conf, cs_conf, shell_path, dependencies_path, resources_conf,
            ftp_conf, tests_conf, dut_shell_path, dut_dependencies_path,
    ):
        """Main config

        :param CloudShellConfig do_conf:
        :param CloudShellConfig cs_conf:
        :param str shell_path:
        :param str dependencies_path:
        :param list[ResourceConfig] resources_conf:
        :param FTPConfig ftp_conf:
        :param TestsConfig tests_conf:
        :param str dut_shell_path:
        :param str dut_dependencies_path:
        """

        self.do = do_conf
        self.cs = cs_conf
        self.shell_path = shell_path
        self.dependencies_path = dependencies_path
        self.resources = resources_conf
        self.ftp = ftp_conf
        self.tests_conf = tests_conf
        self.dut_shell_path = dut_shell_path
        self.dut_dependencies_path = dut_dependencies_path

    @property
    def shell_name(self):
        return re.split(r'[\\/]', self.shell_path)[-1]

    @classmethod
    def parse_config_from_yaml(cls, shell_conf_path, env_conf_path=None):
        env_conf = {}
        if env_conf_path is not None:
            with open(env_conf_path) as f:
                env_conf = yaml.load(f.read())

        with open(shell_conf_path) as f:
            shell_conf = yaml.load(f.read())

        config = merge_dicts(shell_conf, env_conf)

        do_conf = CloudShellConfig.from_dict(config.get('Do'))
        cs_conf = CloudShellConfig.from_dict(config.get('CloudShell'))
        resources = map(ResourceConfig.from_dict, config['Resources'])
        ftp_conf = FTPConfig.from_dict(config.get('FTP'))
        tests_conf = TestsConfig.from_dict(config.get('Tests'))

        return cls(
            do_conf,
            cs_conf,
            config['Shell']['Path'],
            config['Shell'].get('Dependencies Path'),
            resources,
            ftp_conf,
            tests_conf,
            config['DUT Shell Path'],
            config.get('DUT Dependencies Path'),
        )


def merge_dicts(first, second):
    """Create a new dict from two dicts, first replaced second

    :param dict first:
    :param dict second:
    :rtype: dict
    """

    new_dict = second.copy()

    for key, val in first.iteritems():
        if isinstance(val, dict):
            new_dict[key] = merge_dicts(val, new_dict.get(key, {}))
        elif isinstance(val, list):
            lst = second.get(key, [])[:]
            lst.extend(val)
            new_dict[key] = lst
        else:
            new_dict[key] = val

    return new_dict
