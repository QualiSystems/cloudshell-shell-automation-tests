from mock import patch, MagicMock, call

from tests.base_tests import BaseTestCase


@patch('shell_tests.run_tests.is_host_alive')
class TestNetworkingDevice(BaseTestCase):
    def setUp(self):
        super(TestNetworkingDevice, self).setUp()
        self.test_runner = self._get_auto_tests_runner('test_networking_device.yaml')

    @patch('shell_tests.helpers.urllib2.urlopen', MagicMock())
    @patch('shell_tests.helpers.open', MagicMock())
    @patch('shell_tests.helpers.os.mkdir', MagicMock())
    @patch('shell_tests.cs_handler.PackagingRestApiClient', MagicMock())
    @patch('shell_tests.resource_handler.get_resource_family_and_model', MagicMock(return_value=(
            MagicMock(), MagicMock())))
    @patch('shell_tests.shell_handler.zipfile.ZipFile')
    @patch.object('shell_tests.run_tests.RunTestsForResource', 'get_driver_commands')
    @patch('shell_tests.smb_handler.SMBConnection')
    def test_networking_devices(
            self, smb_conn_mock, get_driver_comm_mock, zipfile_shell_handler_mock,
            is_host_alive_mock):

        is_host_alive_mock.return_value = True
        get_driver_comm_mock.return_value = ['run_custom_command', 'run_custom_config_command']
        dependency_files = [MagicMock(), MagicMock(), MagicMock()]
        zip_namelist = [
            'shell-icon.png',
            'ShellNameDriver.zip',
            'shell-definition.yaml',
            'TOSCA-Metadata/',
            'TOSCA-Metadata/TOSCA.meta',
        ]

        zipfile_shell_handler_mock.return_value.__enter__.return_value = MagicMock(
            filelist=dependency_files,
            namelist=MagicMock(return_value=zip_namelist),
            read=MagicMock(return_value=''),
        )

        with self.patch_api([self.cs_api_mock]):
            self.test_runner.run()

        ips_to_test = [
            self.conf.resources[0].device_ip, self.conf.resources[1].device_ip, self.conf.ftp.host,
            self.conf.cs.host
        ]
        self.assertSequenceEqual(is_host_alive_mock.call_args_list, map(call, ips_to_test))
