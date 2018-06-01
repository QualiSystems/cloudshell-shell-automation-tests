import unittest


class BaseTestCase(unittest.TestCase):
    def __init__(self, method_name, resource_handler):
        """Base Test Case

        :param ResourceHandler resource_handler: should be with fake device id
        """

        super(BaseTestCase, self).__init__(method_name)
        self.resource_handler = resource_handler
