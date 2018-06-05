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


class ReportConfig(object):
    def __init__(self, user, password, recipients):
        self.user = user
        self.password = password
        self.recipients = recipients


class ResourceConfig(object):
    def __init__(self, do_conf, cs_conf, report_conf, shell_path, dependencies_path, resource_name,
                 device_ip, attributes):
        """Main config

        :param CloudShellConfig do_conf:
        :param CloudShellConfig cs_conf:
        :param ReportConfig report_conf:
        :param str shell_path:
        :param str dependencies_path:
        :param str resource_name:
        :param str device_ip:
        :param dict attributes:
        """

        self.do = do_conf
        self.cs = cs_conf
        self.report = report_conf
        self.shell_path = shell_path
        self.dependencies_path = dependencies_path
        self.resource_name = resource_name
        self.device_ip = device_ip
        self.attributes = attributes

    @classmethod
    def parse_config_from_yaml(cls, shell_conf_path, env_conf_path=None):
        env_conf = {}
        if env_conf_path is not None:
            with open(env_conf_path) as f:
                env_conf = yaml.load(f.read())

        with open(shell_conf_path) as f:
            shell_conf = yaml.load(f.read())

        config = merge_dicts(shell_conf, env_conf)

        if config.get('Do'):
            do_conf = CloudShellConfig(
                config['Do']['Host'],
                config['Do']['User'],
                config['Do']['Password'],
                domain=config['Do'].get('Domain', CloudShellConfig.DEFAULT_DOMAIN),
            )
        else:
            do_conf = None

        if config.get('CloudShell'):
            cs_conf = CloudShellConfig(
                config['CloudShell']['Host'],
                config['CloudShell']['User'],
                config['CloudShell']['Password'],
                config['CloudShell'].get('OS User'),
                config['CloudShell'].get('OS Password'),
                config['CloudShell'].get('Domain', CloudShellConfig.DEFAULT_DOMAIN),
            )
        else:
            cs_conf = None

        if config.get('Report'):
            report_conf = ReportConfig(
                config['Report']['User'],
                config['Report']['Password'],
                config['Report']['Recipients'],
            )
        else:
            report_conf = None

        return cls(
            do_conf,
            cs_conf,
            report_conf,
            config['Shell']['Path'],
            config['Shell'].get('Dependencies Path'),
            config['Resource']['Name'],
            config['Resource'].get('Device IP'),
            config['Resource'].get('Attributes'),
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
            lst = first.get(key, [])
            lst.extend(val)
            new_dict[key] = lst
        else:
            new_dict[key] = val

    return new_dict
