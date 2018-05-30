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


class ResourceConfig(object):
    def __init__(self, do_conf, cs_conf, shell_path, dependencies_path, resource_name, device_ip,
                 attributes):
        """Main config

        :param CloudShellConfig do_conf:
        :param CloudShellConfig cs_conf:
        :param str shell_path:
        :param str dependencies_path:
        :param str resource_name:
        :param str device_ip:
        :param dict attributes:
        """

        self.do = do_conf
        self.cs = cs_conf
        self.shell_path = shell_path
        self.dependencies_path = dependencies_path
        self.resource_name = resource_name
        self.device_ip = device_ip
        self.attributes = attributes

    @classmethod
    def parse_config_from_yaml(cls, file_name):
        with open(file_name) as f:
            config = yaml.load(f.read())

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

        return cls(
            do_conf,
            cs_conf,
            config['Shell']['Path'],
            config['Shell'].get('Dependencies Path'),
            config['Resource']['Name'],
            config['Resource'].get('Device IP'),
            config['Resource'].get('Attributes'),
        )
