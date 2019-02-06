from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseTestCase


class TestAutoloadNetworkDevices(BaseTestCase):

    def _get_structure(self, resource_info):
        """Get nested resource structure

        :param cloudshell.api.cloudshell_api.ResourceInfo resource_info:
        :return: {'CS_Router': [{'CS_Chassis': ['CS_Port', 'CS_Port', ...], 'CS_PortChannel', ...]}
        :rtype: dict
        """

        if resource_info.ChildResources:
            return {
                resource_info.ResourceFamilyName:
                    sorted([self._get_structure(child) for child in resource_info.ChildResources])
            }

        else:
            return resource_info.ResourceFamilyName

    def test_structure(self):
        self.target_handler.autoload()

        info = self.target_handler.get_details()
        structure = self._get_structure(info)

        self.assertIn('CS_Port', str(structure))


class TestAutoloadTrafficGeneratorDevices(TestAutoloadNetworkDevices):
    def test_structure(self):
        self.target_handler.autoload()

        info = self.target_handler.get_details()
        structure = self._get_structure(info)

        self.assertIn('CS_TrafficGeneratorPort', str(structure))


class TestAutoloadWithoutDevice(BaseTestCase):

    def test_structure(self):
        error_pattern = r'(SessionManagerException|\'ConnectionError\')'

        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            self.target_handler.autoload()
