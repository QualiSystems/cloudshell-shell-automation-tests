from cloudshell.api.cloudshell_api import ResourceInfo
from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseResourceServiceTestCase


class TestAutoloadNetworkDevices(BaseResourceServiceTestCase):
    def _get_structure(self, resource_info: ResourceInfo):
        """Get nested resource structure.

        :return: {
            'CS_Router':
                [{'CS_Chassis': ['CS_Port', 'CS_Port', ...], 'CS_PortChannel', ...]
        }
        """
        if resource_info.ChildResources:
            return {
                resource_info.ResourceFamilyName: [
                    self._get_structure(child) for child in resource_info.ChildResources
                ]
            }
        else:
            return resource_info.ResourceFamilyName

    def test_structure(self):
        self.handler.autoload()
        info = self.handler.get_details()
        structure = self._get_structure(info)
        self.assertIn("CS_Port", str(structure))


class TestAutoloadWithoutPorts(BaseResourceServiceTestCase):
    def test_autoload(self):
        # just test that it runs without errors
        self.handler.autoload()


class TestAutoloadTrafficGeneratorDevices(TestAutoloadNetworkDevices):
    def test_structure(self):
        self.handler.autoload()
        info = self.handler.get_details()
        structure = self._get_structure(info)
        self.assertIn("CS_TrafficGeneratorPort", str(structure))


class TestAutoloadWithoutDevice(BaseResourceServiceTestCase):
    def test_structure(self):
        error_pattern = r"(SessionManagerException|\'ConnectionError\')"
        with self.assertRaisesRegex(CloudShellAPIError, error_pattern):
            self.handler.autoload()


class TestAutoloadVirtualTrafficGeneratorDevices(TestAutoloadNetworkDevices):
    def test_structure(self):
        info = self.handler.get_details()
        structure = self._get_structure(info)
        self.assertIn("CS_VirtualTrafficGeneratorPort", str(structure))


class TestAutoloadShellFromTemplate(BaseResourceServiceTestCase):
    def test_execute_without_error(self):
        self.handler.autoload()
