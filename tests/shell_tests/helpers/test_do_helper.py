import time
from unittest.mock import Mock, call, create_autospec

import pytest
from cloudshell.api.cloudshell_api import (
    CloudShellAPISession,
    CreateReservationResponseInfo,
    ReservationDiagramLayoutResponseInfo,
    ReservationSlimStatusInfo,
    ResourceAttribute,
    ResourceDiagramLayoutInfo,
    ResourceInfo,
    TopologiesByCategoryInfo,
    TopologyAppResourceInfo,
    TopologyInfo,
)

from shell_tests.configs import MainConfig
from shell_tests.errors import CreationReservationError, CSIsNotAliveError
from shell_tests.handlers import cs_handler
from shell_tests.handlers.cs_handler import CloudShellHandler
from shell_tests.handlers.do_handler import DoHandler

from tests.base import CONFIGS_DIR

_DO_TOPOLOGIES_INFO: TopologiesByCategoryInfo = create_autospec(
    TopologiesByCategoryInfo,
    Topologies=[
        "Environments/CloudShell 9.2 GA IL",
        "Environments/CloudShell ES 8.0 GA",
        "Environments/CloudShell 9.0 EA - IL",
        "Environments/Qualix 3.0",
        "Environments/CloudShell 8.3 GA - IL",
        "Environments/CloudShell 9.3 GA IL",
        "Environments/CloudShell ES 8.1 EA",
        "Cloudshell 2020.1 Performance",
        "Environments/CloudShell 8.2 GA P3 - IL",
        "Environments/CloudShell 7.1 GA P9 - IL",
        "Environments/CloudShell 8.1 GA - Distributed",
        "Environments/CloudShell ES 8.2 EA",
        "Environments/CloudShell 8.1 GA P5 - IL",
        "Environments/CloudShell 7.0 GA P11  - IL",
        "Environments/CloudShell 8.0 GA P8 - IL",
    ],
)
_DO_CS_TOPOLOGY_INFO: TopologyInfo = create_autospec(
    TopologyInfo,
    Apps=[create_autospec(TopologyAppResourceInfo, Name="CloudShell 9.3 GA")],
)
_RESERVATION_ID = "f91adb5c-3a5e-4689-98e3-c28be8d4b307"
_CREATE_RESERVATION_INFO: CreateReservationResponseInfo = create_autospec(
    CreateReservationResponseInfo, Reservation=Mock(Id=_RESERVATION_ID)
)
_RESERVATION_STATUS_INFO_SETUP: ReservationSlimStatusInfo = create_autospec(
    ReservationSlimStatusInfo,
    ReservationSlimStatus=Mock(
        ProvisioningStatus="Setup",  # used for checking that reservation is started
        Status="Completed",  # used for checking that reservation is finished
    ),
)
_RESERVATION_STATUS_INFO_READY: ReservationSlimStatusInfo = create_autospec(
    ReservationSlimStatusInfo,
    ReservationSlimStatus=Mock(
        ProvisioningStatus="Ready",  # used for checking that reservation is started
        Status="Completed",  # used for checking that reservation is finished
    ),
)
_CS_IP = "192.168.2.1"
_CS_OS_USER = "cs_os_user"
_CS_OS_PASS = "cs_os_pass"
_CS_RESOURCE_INFO: ResourceInfo = create_autospec(
    ResourceInfo,
    Address=_CS_IP,
    ResourceAttributes=[
        create_autospec(ResourceAttribute, Name="OS Login", Value=_CS_OS_USER),
        create_autospec(ResourceAttribute, Name="OS Password", Value=_CS_OS_PASS),
    ],
)


@pytest.fixture
def conf():
    path = CONFIGS_DIR / "test_tests_conf_in_shell_and_resource.yaml"
    return MainConfig.from_yaml(path)


@pytest.fixture
def sleepless(monkeypatch):
    def sleep(_):
        pass

    monkeypatch.setattr(time, "sleep", sleep)


@pytest.fixture
def api_mock(conf: MainConfig):
    api_mock: CloudShellAPISession = create_autospec(CloudShellAPISession)
    api_mock.username = conf.do_conf.user
    return api_mock


@pytest.fixture
def resource_name_in_do_reservation(conf: MainConfig):
    return f"{conf.do_conf.cs_on_do_conf.cs_version}_cf83-daf3"


@pytest.fixture
def do_reservation_resources_info(resource_name_in_do_reservation):
    return create_autospec(
        ReservationDiagramLayoutResponseInfo,
        ResourceDiagramLayouts=[
            create_autospec(
                ResourceDiagramLayoutInfo, ResourceName=resource_name_in_do_reservation
            )
        ],
    )


def test_do_reservation_is_not_started_in_time(conf, api_mock, sleepless, monkeypatch):
    # setup
    monkeypatch.delattr(CloudShellHandler, "_rest_api")
    monkeypatch.setattr(CloudShellHandler, "_api", api_mock)
    api_mock.GetTopologiesByCategory.return_value = _DO_TOPOLOGIES_INFO
    api_mock.CreateImmediateTopologyReservation.return_value = _CREATE_RESERVATION_INFO
    api_mock.GetReservationStatus.return_value = _RESERVATION_STATUS_INFO_SETUP
    topology_full_name = f"Environments/{conf.do_conf.cs_on_do_conf.cs_version}"

    # run
    do = DoHandler(conf)
    with pytest.raises(
        CreationReservationError, match=r"The reservation \S+ doesn't started"
    ):
        do.prepare()

    # check
    expected_calls = [
        call.GetTopologiesByCategory(""),
        call.CreateImmediateTopologyReservation(
            topology_full_name,
            conf.do_conf.user,
            120,
            topologyFullPath=topology_full_name,
            globalInputs=[],
        ),
        *[call.GetReservationStatus(_RESERVATION_ID)] * 60,
        call.EndReservation(_RESERVATION_ID),
    ]
    assert api_mock.method_calls == expected_calls


def test_cs_is_not_installed_properly_on_do(
    conf,
    api_mock,
    sleepless,
    monkeypatch,
    do_reservation_resources_info,
    resource_name_in_do_reservation,
):
    # setup
    monkeypatch.delattr(CloudShellHandler, "_rest_api")
    monkeypatch.setattr(
        # do API and 10 * 5 APIs for CS that fails
        # 10 times tries for the one CS and tried in 5 CSs
        cs_handler,
        "CloudShellAPISession",
        Mock(side_effect=[api_mock, *[OSError] * 10 * 5]),
    )
    api_mock.GetTopologiesByCategory.return_value = _DO_TOPOLOGIES_INFO
    api_mock.CreateImmediateTopologyReservation.return_value = _CREATE_RESERVATION_INFO
    api_mock.GetReservationStatus.return_value = _RESERVATION_STATUS_INFO_READY
    api_mock.GetTopologyDetails.return_value = _DO_CS_TOPOLOGY_INFO
    api_mock.GetReservationResourcesPositions.return_value = (
        do_reservation_resources_info
    )
    api_mock.GetResourceDetails.return_value = _CS_RESOURCE_INFO
    topology_full_name = f"Environments/{conf.do_conf.cs_on_do_conf.cs_version}"

    # run
    do = DoHandler(conf)
    with pytest.raises(CSIsNotAliveError):
        do.prepare()

    # check
    expected_calls = [
        call.GetTopologiesByCategory(""),
        call.CreateImmediateTopologyReservation(
            topology_full_name,
            conf.do_conf.user,
            120,
            topologyFullPath=topology_full_name,
            globalInputs=[],
        ),
        call.GetReservationStatus(_RESERVATION_ID),
        call.GetTopologyDetails(topology_full_name),
        call.GetReservationResourcesPositions(_RESERVATION_ID),
        call.GetResourceDetails(resource_name_in_do_reservation),
        call.EndReservation(_RESERVATION_ID),
    ] * 5
    expected_calls.append(call.EndReservation(_RESERVATION_ID))
    assert api_mock.method_calls == expected_calls


def test_cs_is_started(
    conf,
    api_mock,
    sleepless,
    monkeypatch,
    do_reservation_resources_info,
    resource_name_in_do_reservation,
):
    # setup
    monkeypatch.delattr(CloudShellHandler, "_rest_api")
    monkeypatch.setattr(CloudShellHandler, "_api", api_mock)
    api_mock.GetTopologiesByCategory.return_value = _DO_TOPOLOGIES_INFO
    api_mock.CreateImmediateTopologyReservation.return_value = _CREATE_RESERVATION_INFO
    api_mock.GetReservationStatus.return_value = _RESERVATION_STATUS_INFO_READY
    api_mock.GetTopologyDetails.return_value = _DO_CS_TOPOLOGY_INFO
    api_mock.GetReservationResourcesPositions.return_value = (
        do_reservation_resources_info
    )
    api_mock.GetResourceDetails.return_value = _CS_RESOURCE_INFO
    topology_full_name = f"Environments/{conf.do_conf.cs_on_do_conf.cs_version}"

    # run
    do = DoHandler(conf)
    do.prepare()

    # check
    assert conf.cs_conf.host == _CS_IP
    expected_calls = [
        call.GetTopologiesByCategory(""),
        call.CreateImmediateTopologyReservation(
            topology_full_name,
            conf.do_conf.user,
            120,
            topologyFullPath=topology_full_name,
            globalInputs=[],
        ),
        call.GetReservationStatus(_RESERVATION_ID),
        call.GetTopologyDetails(topology_full_name),
        call.GetReservationResourcesPositions(_RESERVATION_ID),
        call.GetResourceDetails(resource_name_in_do_reservation),
    ]
    assert api_mock.method_calls == expected_calls

    # finish
    do.finish()
    expected_calls.extend([call.EndReservation(_RESERVATION_ID)])
    assert api_mock.method_calls == expected_calls
