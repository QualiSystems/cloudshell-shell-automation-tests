import unittest


class BaseTestCase(unittest.TestCase):
    def __init__(self, method_name, resource_handler, conf, logger):
        """Base Test Case

        :param str method_name:
        :param shell_tests.resource_handler.ResourceHandler resource_handler:
        :param shell_tests.configs.ShellConfig conf:
        :param logging.Logger logger:
        """

        super(BaseTestCase, self).__init__(method_name)
        self.resource_handler = resource_handler
        self.conf = conf
        self.logger = logger
