from shell_tests.automation_tests.base import BaseTestCase
from shell_tests.dut_handler import DutHandler


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
    def test_connectivity(self):
        cs_handler = self.resource_handler.cs_handler

        with DutHandler(
                cs_handler,
                self.resource_handler.reservation_id,
                self.shell_conf.dut_shell_path,
                self.shell_conf.dut_dependencies_path if self.shell_conf.dependencies_path else None,
                self.logger) as dut_handler:

            res_info = self.resource_handler.get_details()
            dut_info = cs_handler.get_resource_details(dut_handler.name)

            res_port1 = find_port_name(res_info)
            res_port2 = find_port_name(res_info, {res_port1})
            dut_port1 = find_port_name(dut_info)
            dut_port2 = find_port_name(dut_info, {dut_port1})

            # adding physical connections
            cs_handler.add_physical_connection(
                self.resource_handler.reservation_id,
                res_port1,
                dut_port1,
            )
            cs_handler.add_physical_connection(
                self.resource_handler.reservation_id,
                res_port2,
                dut_port2,
            )

            # add VLAN
            cs_handler.connect_ports_with_connector(
                self.resource_handler.reservation_id,
                dut_port1,
                dut_port2,
                'dut-connector',
            )

            # remove VLAN
            cs_handler.remove_connector(
                self.resource_handler.reservation_id,
                dut_port1,
                dut_port2,
            )
