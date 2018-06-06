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
        return cls(
            config['Host'],
            config['User'],
            config['Password'],
            config.get('OS User'),
            config.get('OS Password'),
            config.get('Domain', CloudShellConfig.DEFAULT_DOMAIN),
        )


class ReportConfig(object):
    def __init__(self, user, password, recipients):
        self.user = user
        self.password = password
        self.recipients = recipients

    @classmethod
    def from_dict(cls, config):
        return cls(
            config['Report']['User'],
            config['Report']['Password'],
            config['Report']['Recipients'],
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
        return cls(
            config['Name'],
            config.get('Device IP'),
            config.get('Attributes'),
        )


class ShellConfig(object):
    def __init__(
            self, do_conf, cs_conf, report_conf, shell_path, dependencies_path, resources_conf):
        """Main config

        :param CloudShellConfig do_conf:
        :param CloudShellConfig cs_conf:
        :param ReportConfig report_conf:
        :param str shell_path:
        :param str dependencies_path:
        :param list[ResourceConfig] resources_conf:
        """

        self.do = do_conf
        self.cs = cs_conf
        self.report = report_conf
        self.shell_path = shell_path
        self.dependencies_path = dependencies_path
        self.resources = resources_conf

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

        do_conf = CloudShellConfig.from_dict(config['Do']) if 'Do' in config else None
        cs_conf = (CloudShellConfig.from_dict(config['CloudShell'])
                   if 'CloudShell' in config else None)
        report_conf = ReportConfig.from_dict(config) if 'Report' in config else None
        resources = map(ResourceConfig.from_dict, config['Resources'])

        return cls(
            do_conf,
            cs_conf,
            report_conf,
            config['Shell']['Path'],
            config['Shell'].get('Dependencies Path'),
            resources,
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
            lst = second.get(key, [])
            lst.extend(val)
            new_dict[key] = lst
        else:
            new_dict[key] = val

    return new_dict
