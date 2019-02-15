from mock import patch, MagicMock, call

from tests.base_tests import BaseTestCase, CS_USER


@patch('shell_tests.run_tests.is_host_alive')
@patch('shell_tests.cs_handler.time', MagicMock())
class TestNetworkingDevice(BaseTestCase):
    def setUp(self):
        super(TestNetworkingDevice, self).setUp()
        self.test_runner = self._get_auto_tests_runner('test_networking_device.yaml')

    @patch('shell_tests.helpers.urllib2.urlopen', MagicMock())
    @patch('shell_tests.helpers.open', MagicMock())
    @patch('shell_tests.helpers.os.mkdir', MagicMock())
    @patch('shell_tests.cs_handler.PackagingRestApiClient', MagicMock())
    @patch('shell_tests.run_tests_for_sandbox.TeamcityTestRunner', MagicMock())
    @patch('shell_tests.run_tests_for_sandbox.unittest.TextTestRunner', MagicMock())
    @patch('shell_tests.shell_handler.os.remove', MagicMock())
    @patch('shell_tests.cs_handler.shutil.rmtree', MagicMock())
    @patch('shell_tests.shell_handler.zipfile.ZipFile')
    @patch('shell_tests.run_tests_for_sandbox.get_driver_commands')
    @patch('shell_tests.smb_handler.SMBConnection')
    @patch('shell_tests.shell_handler.get_resource_family_and_model')
    def test_networking_devices(
            self, get_family_and_model_mock, smb_conn_mock, get_driver_comm_mock,
            zipfile_shell_handler_mock, is_host_alive_mock):
        # check preparing resource without executing tests
        # init
        res_family, res_model = 'CS_Router', MagicMock()
        get_family_and_model_mock.return_value = res_family, res_model
        is_host_alive_mock.return_value = True
        get_driver_comm_mock.return_value = [
            'run_custom_command', 'run_custom_config_command', 'save', 'orchestration_save',
            'restore', 'orchestration_restore', 'applyconnectivitychanges',
        ]
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

        # run
        with self.patch_api([self.cs_api_mock]):
            self.test_runner.run()

        # verify
        # check that all resources was tested with ping
        ips_to_test = [
            r.device_ip for r in self.conf.resources_conf.values() if r.device_ip is not None]
        ips_to_test.extend([self.conf.ftp_conf.host, self.conf.cs_conf.host])
        self.assertSequenceEqual(is_host_alive_mock.call_args_list, map(call, ips_to_test))

        # check that correct commands was sent to CS via API
        self.cs_api_mock.CreateImmediateReservation.assert_called_once_with(
            'first', CS_USER, 120)
        self.cs_api_mock.CreateResource.assert_called_once_with(
            res_family, res_model, self.conf.resources_conf.keys()[0], '127.0.0.1')
        self.cs_api_mock.AddResourcesToReservation.assert_called_once_with(
            self._cs_reservation_ids[0], [self.conf.resources_conf.keys()[0]])

        self.cs_api_mock.SetAttributesValues.assert_called_once()
        res_attr_update_req = self.cs_api_mock.SetAttributesValues.call_args[0][0][0]
        self.assertEqual(res_attr_update_req.ResourceFullName, self.conf.resources_conf.keys()[0])
        attrs_dict = {attr_val.Name: attr_val.Value
                      for attr_val in res_attr_update_req.AttributeNamesValues}
        self.assertEqual(
            attrs_dict,
            {'{}.{}'.format(res_model, key): val
             for key, val in self.conf.resources_conf.values()[0].attributes.items()}
        )

        self.cs_api_mock.EndReservation.assert_called_once_with(self._cs_reservation_ids[0])
        self.cs_api_mock.GetReservationStatus.assert_called_with(self._cs_reservation_ids[0])
        self.cs_api_mock.DeleteReservation.assert_called_once_with(self._cs_reservation_ids[0])
        self.cs_api_mock.DeleteResource.assert_called_once_with(self.conf.resources_conf.keys()[0])

        executed_method_names = [call_[0] for call_ in self.cs_api_mock.method_calls]
        expected_method_names = [
            'CreateImmediateReservation',
            'CreateResource',
            'SetAttributesValues',
            'AddResourcesToReservation',
            'EndReservation',
            'GetReservationStatus',
            'GetReservationStatus',
            'DeleteReservation',
            'DeleteResource',
        ]
        self.assertSequenceEqual(executed_method_names, expected_method_names)
