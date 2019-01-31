from mock import MagicMock, patch, call

from shell_tests.errors import ResourceIsNotAliveError, CSIsNotAliveError, BaseAutomationException
from tests.base_tests import BaseTestCase


@patch('shell_tests.run_tests.is_host_alive')
@patch('shell_tests.do_handler.time', MagicMock())
class TestCreatingCloudShellInDo(BaseTestCase):

    def setUp(self):
        super(TestCreatingCloudShellInDo, self).setUp()
        self.test_runner = self._get_auto_tests_runner('test_creating_cloudshell.yaml')

    def test_cloudshell_is_not_alive(self, is_host_alive_mock):
        is_host_alive_mock.return_value = True

        self.do_api_mock.GetReservationStatus.side_effect = [
            # first CS
            MagicMock(ReservationSlimStatus=MagicMock(ProvisioningStatus='Ready')),
            MagicMock(ReservationSlimStatus=MagicMock(Status='Completed')),
            # second CS
            MagicMock(ReservationSlimStatus=MagicMock(ProvisioningStatus='Ready')),
            MagicMock(ReservationSlimStatus=MagicMock(Status='Completed')),
            # third CS
            MagicMock(ReservationSlimStatus=MagicMock(ProvisioningStatus='Ready')),
            MagicMock(ReservationSlimStatus=MagicMock(Status='Completed')),
            # fourth Cs
            MagicMock(ReservationSlimStatus=MagicMock(ProvisioningStatus='Ready')),
            MagicMock(ReservationSlimStatus=MagicMock(Status='Completed')),
            # fifth CS
            MagicMock(ReservationSlimStatus=MagicMock(ProvisioningStatus='Ready')),
            MagicMock(ReservationSlimStatus=MagicMock(Status='Completed')),
        ]

        with self.patch_api((self.do_api_mock, IOError, IOError, IOError, IOError, IOError)):
            with self.assertRaises(CSIsNotAliveError):
                self.test_runner.run()

    @patch('shell_tests.run_tests.RunTestsInCloudShell')
    def test_cloudshell_is_alive(self, run_tests_mock, is_host_alive_mock):
        # don't run tests
        run_tests_inst = MagicMock()
        run_tests_mock.return_value = run_tests_inst

        with self.patch_api((self.do_api_mock, MagicMock())):
            self.test_runner.run()

        run_tests_inst.run.assert_called_once()
        self.assertSequenceEqual(
            is_host_alive_mock.call_args_list,
            map(call, [self.conf.ftp_conf.host, self.conf.do_conf.host])
        )

    def test_resource_is_not_alive(self, is_host_alive_mock):
        is_host_alive_mock.return_value = False

        with self.patch_api():
            with self.assertRaises(ResourceIsNotAliveError):
                self.test_runner.run()

    def test_get_not_available_cs_version(self, is_host_alive_mock):
        is_host_alive_mock.return_value = True
        self.conf.do_conf.cs_version = 'CloudShell 8.4'

        with self.patch_api():
            with self.assertRaisesRegexp(BaseAutomationException, r'version .+ isn\'t correct'):
                self.test_runner.run()

    def test_cloudshell_dont_starts(self, is_host_alive_mock):
        is_host_alive_mock.return_value = True
        reservation_status = [
            MagicMock(ReservationSlimStatus=MagicMock(ProvisioningStatus='Setup'))] * 30
        # end do reservation
        reservation_status.append(MagicMock(ReservationSlimStatus=MagicMock(Status='Completed')))
        self.do_api_mock.GetReservationStatus.side_effect = reservation_status

        with self.patch_api():
            with self.assertRaisesRegexp(BaseAutomationException, r'CloudShell isn\'t started'):
                self.test_runner.run()

    def test_do_fail_to_end_reservation(self, is_host_alive_mock):
        is_host_alive_mock.return_value = True  # todo move it to setup; p = patch(); p.start; p.stop()
        reservation_status = [
            MagicMock(ReservationSlimStatus=MagicMock(ProvisioningStatus='Ready'))]
        # end do reservation
        reservation_status.extend(
            [MagicMock(ReservationSlimStatus=MagicMock(Status='Teardown'))] * 30)
        self.do_api_mock.GetReservationStatus.side_effect = reservation_status

        with self.patch_api():
            with self.assertRaisesRegexp(BaseAutomationException, r'Can\'t end reservation'):
                self.test_runner.run()
