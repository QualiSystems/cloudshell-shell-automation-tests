import os
import unittest
import uuid

from cloudshell.api.cloudshell_api import CloudShellAPISession
from mock import patch, MagicMock, create_autospec

from shell_tests.configs import ShellConfig
from shell_tests.run_tests import AutomatedTestsRunner


CONFIGS_PATH = os.path.abspath('./test_configs')
CS_TOPOLOGIES = [
    'Environment/CloudShell 8.3 GA',
    'Environment/CloudShell - Latest 8.3',
]
DO_USER = 'user'
CS_RESERVATION_ID = str(uuid.uuid4())
CS_IP = '192.168.100.2'
CS_USER = 'cs_user'
CS_OS_USER = 'cs_os_user'
CS_OS_PASSWORD = 'cs_os_password'


class BaseTestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(BaseTestCase, self).__init__(*args, **kwargs)
        self._cs_reservation_ids = []

    @staticmethod
    def _get_do_api_mock():
        """Create mock object for the API that uses in DO handler."""
        do_api_mock = create_autospec(CloudShellAPISession)
        do_api_mock.GetTopologiesByCategory.return_value.Topologies = CS_TOPOLOGIES
        do_api_mock.CreateImmediateTopologyReservation.return_value.Reservation.Id = \
            CS_RESERVATION_ID
        do_api_mock.username = DO_USER
        do_api_mock.GetReservationStatus.side_effect = [
            # creating cs
            MagicMock(ReservationSlimStatus=MagicMock(ProvisioningStatus='Setup')),
            MagicMock(ReservationSlimStatus=MagicMock(ProvisioningStatus='Ready')),
            # deleting cs
            MagicMock(ReservationSlimStatus=MagicMock(Status='Teardown')),
            MagicMock(ReservationSlimStatus=MagicMock(Status='Completed')),
        ]
        do_api_mock.GetReservationDetails.return_value.ReservationDescription.Resources.Name = \
            'CloudShell 8.3 GA fadf'
        do_api_mock.GetResourceDetails.return_value = MagicMock(
            FullAddress=CS_IP,
            ResourceAttributes=[
                MagicMock(Name='OS Login', Value=CS_OS_USER),
                MagicMock(Name='OS Password', Value=CS_OS_PASSWORD),
            ])

        return do_api_mock

    def _get_cs_reservation_id(self, *args, **kwargs):
        id_ = str(uuid.uuid4())
        self._cs_reservation_ids.append(id_)
        return MagicMock(Reservation=MagicMock(Id=id_))

    def _get_cs_api_mock(self):
        """Create mock object for the API that uses in CS handler."""
        cs_api_mock = create_autospec(CloudShellAPISession)
        cs_api_mock.CreateImmediateReservation.side_effect = self._get_cs_reservation_id
        cs_api_mock.username = CS_USER

        return cs_api_mock

    def _get_auto_tests_runner(self, shell_conf_name):
        shell_conf_path = os.path.join(CONFIGS_PATH, shell_conf_name)
        self.conf = ShellConfig.parse_config_from_yaml(shell_conf_path)

        return AutomatedTestsRunner(self.conf, self.logger)

    def patch_api(self, api_sessions=None):
        if api_sessions is None:
            api_sessions = (self.do_api_mock, )

        api_sessions_mock = MagicMock(side_effect=api_sessions)

        return patch('shell_tests.cs_handler.CloudShellAPISession', api_sessions_mock)

    def setUp(self):
        self.logger = MagicMock()
        self.do_api_mock = self._get_do_api_mock()
        self.cs_api_mock = self._get_cs_api_mock()
