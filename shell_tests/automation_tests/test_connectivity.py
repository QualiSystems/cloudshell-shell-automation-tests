import itertools
from contextlib import contextmanager
from threading import Lock
from typing import TYPE_CHECKING

from cloudshell.api.cloudshell_api import ResourceInfo

from shell_tests.automation_tests.base import BaseResourceServiceTestCase
from shell_tests.errors import BaseAutomationException

if TYPE_CHECKING:
    from shell_tests.handlers.resource_handler import ResourceHandler


def find_ports(resource_info: ResourceInfo) -> list[ResourceInfo]:
    if resource_info.ResourceFamilyName == "CS_Port":
        ports = [resource_info]
    elif resource_info.ChildResources:
        ports = list(itertools.chain(*map(find_ports, resource_info.ChildResources)))
    else:
        ports = []
    return ports


def get_port_names_for_connectivity(resource_info: ResourceInfo) -> tuple[str, str]:
    ports = find_ports(resource_info)
    try:
        port1_name, port2_name = ports[0].Name, ports[1].Name
    except IndexError:
        raise BaseAutomationException(
            f"Resource {resource_info.Name} has too few ports for "
            f"connectivity {len(ports)}"
        )
    return port1_name, port2_name


class TestConnectivity(BaseResourceServiceTestCase):
    LOCK = Lock()

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

    @contextmanager
    def dut_handler(self):
        dut_handler = self.get_other_device_for_connectivity()
        dut_handler.autoload_finished.wait(600)
        self.handler.sandbox_handler.add_resource_to_reservation(dut_handler)
        try:
            yield dut_handler
        finally:
            self.handler.sandbox_handler.remove_resource_from_reservation(dut_handler)

    def test_connectivity(self):
        with self.LOCK, self.dut_handler() as dut_handler:
            self._test_connectivity(dut_handler)

    def _test_connectivity(self, dut_handler: "ResourceHandler"):
        for handler in (self.handler, dut_handler):
            if (
                not handler.autoload_finished.is_set()
                or not handler.is_autoload_success
            ):
                raise BaseAutomationException(
                    f"Autoload doesn't finish for the {handler.name} resource,"
                    f" so skip testing connectivity"
                )

        res_info = self.handler.get_details()
        dut_info = dut_handler.get_details()

        res_port1, res_port2 = get_port_names_for_connectivity(res_info)
        dut_port1, dut_port2 = get_port_names_for_connectivity(dut_info)

        # adding physical connections
        self.handler.sandbox_handler.add_physical_connection(res_port1, dut_port1)
        self.handler.sandbox_handler.add_physical_connection(res_port2, dut_port2)

        # add VLAN
        self.handler.sandbox_handler.connect_ports_with_connector(
            dut_port1, dut_port2, "connector"
        )

        # remove VLAN
        self.handler.sandbox_handler.remove_connector(dut_port1, dut_port2)
