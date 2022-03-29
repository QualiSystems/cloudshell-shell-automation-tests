import re

from shell_tests.automation_tests.base import BaseSandboxTestCase
from shell_tests.errors import BaseAutomationException
from shell_tests.helpers.vm_helpers import (
    get_str_connections_form_blueprint,
    parse_connections,
)


class AppNetworkInfo:
    def __init__(self, vm_name, cs_name, blueprint_name, vm_uuid):
        self.vm_name = vm_name
        self.cs_name = cs_name
        self.blueprint_name = blueprint_name
        self.vm_uuid = vm_uuid
        self.ports: dict[str, PortInfo] = {}


class PortInfo:
    def __init__(self, mac, adapter_name, port_group_name):
        self.mac = mac
        self.adapter_name = adapter_name
        self.port_group_name = port_group_name

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise ValueError

        return all(
            (
                self.mac == other.mac,
                self.adapter_name == other.adapter_name,
                self.port_group_name == other.port_group_name,
            )
        )

    def __str__(self):
        return (
            f'PortInfo(mac="{self.mac}", '
            f'adapter_name="{self.adapter_name}", '
            f'port_group_name="{self.port_group_name}")'
        )


class TestVMConnections(BaseSandboxTestCase):
    @staticmethod
    def _get_port_info_from_vm_details_network_data(network_data):
        attrs = {attr.Name: attr.Value for attr in network_data.AdditionalData}
        try:
            port_info = PortInfo(
                attrs["mac address"],
                attrs["network adapter"],
                attrs["port group name"],
            )
        except KeyError:
            raise BaseAutomationException(
                "Cannot get all needed information about port from cs. "
                'We need: "mac address", "network adapter", "port group name". '
                "We have: {}".format(attrs)
            )

        return port_info

    def _get_port_info_from_vcenter(self, vm_uuid, adapter_name):
        vm = self.sandbox_handler.vcenter_handler.get_vm_by_uuid(vm_uuid)

        for device in vm.config.hardware.device:
            if device.deviceInfo.label == adapter_name:
                break
        else:
            raise BaseAutomationException(
                f"Cannot find adapter {adapter_name} on vCenter",
            )

        port_group_key = device.backing.port.portgroupKey

        for network in vm.network:
            if getattr(network, "key", "") == port_group_key:
                break
        else:
            raise BaseAutomationException(
                'Cannot find network on the vCenter by portgroupKey "{}"'.format(
                    port_group_key
                ),
            )

        return PortInfo(device.macAddress, adapter_name, network.name)

    def test_vm_connections(self):
        apps_info = {}

        for handler in self.sandbox_handler.deployment_resource_handlers:
            vm_details = handler.get_details().VmDetails
            app_info = AppNetworkInfo(
                handler.vm_name, handler.name, handler._blueprint_name, vm_details.UID
            )
            apps_info[app_info.blueprint_name] = app_info

            for network_data in vm_details.NetworkData:
                cs_port_info = self._get_port_info_from_vm_details_network_data(
                    network_data
                )
                vm_port_info = self._get_port_info_from_vcenter(
                    app_info.vm_uuid, cs_port_info.adapter_name
                )
                self.assertEqual(
                    cs_port_info,
                    vm_port_info,
                    f"Information about the port from CloudShell and from vCenter is "
                    f"different.\nCS port info: {cs_port_info}\n"
                    f"vCenter port info: {vm_port_info}",
                )
                app_info.ports[vm_port_info.adapter_name] = vm_port_info

        self._test_correct_port_group_from_blueprint(apps_info)

    def _find_port_in_app_info_with_conn_name(self, app_info, conn_name):
        if conn_name == "any":
            return None

        port_regex = re.compile(rf"\W{conn_name}$")
        for port_name, port_info in app_info.ports.items():
            if port_regex.search(port_name):
                break
        else:
            self.fail(
                f"Cannot find the port in ports: {app_info.ports.values()}\n "
                f'by using connection name: "{conn_name}"'
            )

        return port_info

    def _test_connection_with_one_specified_port(
        self, specified_port_info, other_app_info
    ):
        self.assertIn(
            specified_port_info.port_group_name,
            [port_info.port_group_name for port_info in other_app_info.ports.values()],
        )

    def _test_correct_port_group_from_blueprint(self, apps_info):
        connections_from_blueprint = parse_connections(
            *get_str_connections_form_blueprint(
                self.sandbox_handler.blueprint_handler.path,
                self.sandbox_handler.blueprint_name,
            )
        )

        for (
            (source_name, source_conn_name),
            target_conns,
        ) in connections_from_blueprint.items():
            for target_name, target_conn_name in target_conns:
                source_app_info = apps_info[source_name]
                target_app_info = apps_info[target_name]

                source_port_info = self._find_port_in_app_info_with_conn_name(
                    source_app_info, source_conn_name
                )
                target_port_info = self._find_port_in_app_info_with_conn_name(
                    target_app_info, target_conn_name
                )

                if source_port_info and target_port_info:
                    self.assertEqual(
                        source_port_info.port_group_name,
                        target_port_info.port_group_name,
                        f"Should be the same port group of the source port "
                        f"{source_app_info} and target port {target_port_info} "
                        f"but it's different",
                    )
                elif source_port_info is target_port_info is None:
                    # we didn't specify ports in blueprint
                    self.assertEqual(len(connections_from_blueprint.keys()), 1)
                    self.assertEqual(len(connections_from_blueprint.values()[0]), 1)
                    self.assertEqual(len(source_app_info.ports), 1)
                    self.assertEqual(len(target_app_info.ports), 1)
                    self.assertEqual(
                        source_app_info.ports.values()[0].port_group_name,
                        target_app_info.ports.values()[0].port_group_name,
                    )
                else:
                    # we specified a port only from one side
                    if source_port_info:
                        self._test_connection_with_one_specified_port(
                            source_port_info, target_app_info
                        )
                    else:
                        self._test_connection_with_one_specified_port(
                            target_port_info, source_app_info
                        )
