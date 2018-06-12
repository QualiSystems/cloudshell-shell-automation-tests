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

    def setUp(self):
        if self.conf.tests_conf and self._testMethodName in self.conf.tests_conf.exclude:
            reason = self.conf.tests_conf.exclude[self._testMethodName]
            self.logger.debug(
                'Skipping test {}, because setting in config file: {}'.format(
                    self._testMethodName, reason))
            self.skipTest('Skipping test because setting in config file: {}'.format(reason))
