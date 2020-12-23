from shell_tests.automation_tests.base import BaseResourceServiceTestCase
from shell_tests.errors import BaseAutomationException


def find_port_name(resource_info, excluded=None):
    """Find port name.

    :param cloudshell.api.cloudshell_api.ResourceInfo resource_info:
    :param set excluded:
    :return: port name
    """
    if excluded is None:
        excluded = set()

    if resource_info.ResourceFamilyName == "CS_Port":
        name = resource_info.Name
        if name not in excluded:
            return name

    else:
        for child in resource_info.ChildResources:
            name = find_port_name(child, excluded)
            if name and name not in excluded:
                return name


class TestConnectivity(BaseResourceServiceTestCase):
    def get_other_device_for_connectivity(self):
        sandbox_resources_handlers = [
            handler
            for handler in self.handler_storage.resource_handlers
            if handler.conf.name in self.handler.sandbox_handler.conf.resource_names
        ]
        for resource_handler in sandbox_resources_handlers:
            if self.handler != resource_handler:
                other_resource = resource_handler
                return other_resource

        raise BaseAutomationException(
            f"You have to add an additional resource to the sandbox "
            f"{self.handler.sandbox_handler.conf.name} for connectivity tests"
        )

    def test_connectivity(self):
        other_target_handler = self.get_other_device_for_connectivity()

        for handler in (self.handler, other_target_handler):
            if not handler.is_autoload_finished:
                raise BaseAutomationException(
                    f"Autoload doesn't finish for the {handler.name} resource,"
                    f" so skip testing connectivity"
                )

        res_info = self.handler.get_details()
        dut_info = other_target_handler.get_details()

        res_port1 = find_port_name(res_info)
        res_port2 = find_port_name(res_info, {res_port1})
        dut_port1 = find_port_name(dut_info)
        dut_port2 = find_port_name(dut_info, {dut_port1})

        # adding physical connections
        self.handler.sandbox_handler.add_physical_connection(res_port1, dut_port1)
        self.handler.sandbox_handler.add_physical_connection(res_port2, dut_port2)

        # add VLAN
        self.handler.sandbox_handler.connect_ports_with_connector(
            dut_port1, dut_port2, "connector"
        )

        # remove VLAN
        self.handler.sandbox_handler.remove_connector(dut_port1, dut_port2)
