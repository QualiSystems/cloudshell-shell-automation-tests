from shell_tests.automation_tests.base import BaseSandboxTestCase
from shell_tests.errors import BaseAutomationException


class AppNetworkInfo(object):
    def __init__(self, vm_name, cs_name, vm_uuid):
        self.vm_name = vm_name
        self.cs_name = cs_name
        self.vm_uuid = vm_uuid
        self.ports = {}  # type: dict[str, PortInfo]


class PortInfo(object):
    def __init__(self, mac, adapter_name, port_group_name):
        self.mac = mac
        self.adapter_name = adapter_name
        self.port_group_name = port_group_name

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise ValueError

        return all((
            self.mac == other.mac,
            self.adapter_name == other.adapter_name,
            self.port_group_name == other.port_group_name,
        ))


class TestVMConnections(BaseSandboxTestCase):
    @staticmethod
    def _get_port_info_from_vm_details_network_data(network_data):
        attrs = {attr.Name: attr.Value for attr in network_data.AdditionalData}
        try:
            port_info = PortInfo(
                attrs['mac address'],
                attrs['network adapter'],
                attrs['port group name'],
            )
        except KeyError:
            raise BaseAutomationException(
                'Cannot get all needed information about port from cs. '
                'We need: "mac address", "network adapter", "port group name". '
                'We have: {}'.format(attrs)
            )

        return port_info

    def _get_port_info_from_vcenter(self, vm_uuid, adapter_name):
        vm = self.sandbox_handler.vcenter_handler.get_vm_by_uuid(vm_uuid)

        for device in vm.config.hardware.device:
            if device.deviceInfo.label == adapter_name:
                break
        else:
            raise BaseAutomationException(
                'Cannot find adapter {} on vCenter'.format(adapter_name),
            )

        port_group_key = device.backing.port.portgroupKey

        for network in vm.network:
            if getattr(network, 'key', '') == port_group_key:
                break
        else:
            raise BaseAutomationException(
                'Cannot find network on the vCenter by portgroupKey "{}"'.format(port_group_key),
            )

        return PortInfo(
            device.macAddress,
            adapter_name,
            network.name,
        )

    def test_vm_connections(self):
        apps_info = {}

        for handler in self.sandbox_handler.deployment_resource_handlers:
            app_info = AppNetworkInfo(
                handler.vm_name,
                handler.name,
                handler.resource_details.VmDetails.UID,
            )
            apps_info[app_info.cs_name] = app_info

            for network_data in handler.resource_details.VmDetails.NetworkData:
                cs_port_info = self._get_port_info_from_vm_details_network_data(network_data)
                vm_port_info = self._get_port_info_from_vcenter(
                    app_info.vm_uuid,
                    cs_port_info.adapter_name,
                )
                self.assertEqual(cs_port_info, vm_port_info)
                app_info.ports[cs_port_info.adapter_name] = cs_port_info

        print apps_info
