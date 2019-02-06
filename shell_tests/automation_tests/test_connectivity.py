from shell_tests.automation_tests.base import BaseTestCase
from shell_tests.errors import BaseAutomationException


def find_port_name(resource_info, excluded=None):
    """
    :param cloudshell.api.cloudshell_api.ResourceInfo resource_info:
    :param set excluded:
    :return: port name
    """

    if excluded is None:
        excluded = set()

    if resource_info.ResourceFamilyName == 'CS_Port':
        name = resource_info.Name
        if name not in excluded:
            return name

    else:
        for child in resource_info.ChildResources:
            name = find_port_name(child, excluded)
            if name and name not in excluded:
                return name


class TestConnectivity(BaseTestCase):
    def get_other_device_for_connectivity(self):
        for resource_handler in self.sandbox_handler.resource_handlers:
            if self.target_handler != resource_handler:
                other_resource = resource_handler
                other_resource.autoload()
                return other_resource

        raise BaseAutomationException('You have to add an additional resource to the sandbox {} '
                                      'for connectivity tests'.format(self.sandbox_handler.name))

    def test_connectivity(self):
        cs_handler = self.target_handler.cs_handler
        other_handler = self.get_other_device_for_connectivity()

        res_info = self.target_handler.get_details()
        dut_info = cs_handler.get_resource_details(other_handler.name)

        res_port1 = find_port_name(res_info)
        res_port2 = find_port_name(res_info, {res_port1})
        dut_port1 = find_port_name(dut_info)
        dut_port2 = find_port_name(dut_info, {dut_port1})

        # adding physical connections
        cs_handler.add_physical_connection(
            self.target_handler.reservation_id,
            res_port1,
            dut_port1,
        )
        cs_handler.add_physical_connection(
            self.sandbox_handler.reservation_id,
            res_port2,
            dut_port2,
        )

        # add VLAN
        cs_handler.connect_ports_with_connector(
            self.sandbox_handler.reservation_id,
            dut_port1,
            dut_port2,
            'connector',
        )

        # remove VLAN
        cs_handler.remove_connector(
            self.sandbox_handler.reservation_id,
            dut_port1,
            dut_port2,
        )
