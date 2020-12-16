from itertools import chain

from shell_tests.handlers.resource_handler import DeviceType


class SandboxReport:
    def __init__(self, sandbox_name: str, is_success: bool, test_result: str):
        self.name = sandbox_name
        self.sandbox_is_success = is_success
        self.test_result = test_result
        self.resources_reports: list[ResourceReport] = []
        self.deployment_resources_reports: list[DeploymentResourceReport] = []
        self.services_reports: list[ServiceReport] = []

    @property
    def is_success(self) -> bool:
        children_success = all(
            r.is_success for r in chain(self.resources_reports, self.services_reports)
        )
        if len(self.resources_reports) == 0 and len(self.services_reports) == 0:
            return False
        return children_success and self.sandbox_is_success

    def __str__(self):
        sandbox_tests_result = ""
        if self.test_result:
            sandbox_tests_result = (
                f"Sandbox name: {self.name}\nTests for sandbox was "
                f"{success_str(self.is_success)}\n{self.test_result}\n\n"
            )

        resources_tests_result = "\n\n".join(map(str, self.resources_reports))
        deployment_resources_tests_result = "\n\n".join(
            map(str, self.deployment_resources_reports)
        )
        services_tests_result = "\n\n".join(map(str, self.services_reports))

        result = (
            f"Sandbox name: {self.name}\n"
            f"Tests for sandbox, resources and services was "
            f"{success_str(self.is_success)}\n\n"
            f"{sandbox_tests_result}{resources_tests_result}"
            f"{deployment_resources_tests_result}{services_tests_result}"
        )
        return result


class ResourceReport:
    def __init__(
        self,
        resource_name: str,
        device_ip: str,
        device_type: DeviceType,
        family: str,
        is_success: bool,
        test_result: str,
    ):
        self.name = resource_name
        self.ip = device_ip
        self.device_type = device_type
        self.family = family
        self.is_success = is_success
        self.test_result = test_result

    def __str__(self):
        result = (
            f"Resource name: {self.name}, IP: {self.ip}, Type: {self.device_type}, "
            f"Family: {self.family}\nTest for the device was "
            f"{success_str(self.is_success)}\n{self.test_result}"
        )
        return result


class DeploymentResourceReport(ResourceReport):
    def __str__(self):
        result = super().__str__()
        result = result.replace("Resource name", "Deployment Resource name")
        return result


class ServiceReport:
    def __init__(
        self,
        service_name: str,
        device_type: str,
        family: str,
        is_success: bool,
        test_result: str,
    ):
        self.name = service_name
        self.device_type = device_type
        self.family = family
        self.is_success = is_success
        self.test_result = test_result

    def __str__(self):
        result = (
            f"Service name: {self.name}, Type: {self.device_type}, "
            f"Family: {self.family}\nTest for the service was "
            f"{success_str(self.is_success)}\n{self.test_result}"
        )
        return result


class Reporting:
    def __init__(self):
        self.sandboxes_reports: list[SandboxReport] = []

    @property
    def is_success(self) -> bool:
        return all(sandbox.is_success for sandbox in self.sandboxes_reports)

    def __str__(self):
        join_str = f"\n\n{'-' * 100}\n\n"
        sandboxes_tests_result = join_str.join(map(str, self.sandboxes_reports))
        return f"Tests was {success_str(self.is_success)}\n\n{sandboxes_tests_result}"


def success_str(is_success: bool) -> str:
    return "successful" if is_success else "unsuccessful"
