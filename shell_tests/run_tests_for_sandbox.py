import threading
from functools import cached_property
from typing import List

from shell_tests.handlers.resource_handler import ResourceHandler
from shell_tests.handlers.sandbox_handler import SandboxHandler
from shell_tests.helpers.handler_storage import HandlerStorage
from shell_tests.helpers.tests_helpers import (
    get_test_runner,
    get_test_suite,
    run_test_suite,
)
from shell_tests.report_result import Reporting, ResourceReport, SandboxReport


class RunTestsForSandbox(threading.Thread):
    REPORT_LOCK = threading.Lock()

    def __init__(
        self,
        sandbox_handler: SandboxHandler,
        handler_storage: HandlerStorage,
        reporting: Reporting,
    ):
        """Run Tests based on the Sandbox."""
        super().__init__(name=f"Thread-{sandbox_handler.conf.name}")

        self.sandbox_handler = sandbox_handler
        self.handler_storage = handler_storage
        self.reporting = reporting

        self._stop_flag = False
        self._current_test_suite = None
        self._test_runner = None

    @cached_property
    def resource_handlers(self) -> List[ResourceHandler]:
        handlers = [
            self.handler_storage.resource_handlers_dict[name]
            for name in self.sandbox_handler.conf.resource_names
        ]
        for handler in handlers:
            self.sandbox_handler.add_resource_to_reservation(handler)
        return handlers

    def stop(self):
        if self._current_test_suite:
            self._current_test_suite.stop()
        self._stop_flag = True

    def run(self):
        """Run tests for the Sandbox and resources."""
        if self._stop_flag:
            raise KeyboardInterrupt
        sandbox_report = self._run_sandbox_tests()

        for resource_handler in self.resource_handlers:
            resource_handler.run_resource_commands(resource_handler.conf.setup_commands)
            if resource_handler.conf.tests_conf.run_tests:
                resource_report = self._run_resource_tests(resource_handler)
                sandbox_report.resources_reports.append(resource_report)
                resource_handler.run_resource_commands(
                    resource_handler.conf.teardown_commands
                )

        with self.REPORT_LOCK:
            self.reporting.sandboxes_reports.append(sandbox_report)

    def _run_sandbox_tests(self) -> SandboxReport:
        return SandboxReport(self.sandbox_handler.conf.name, True, "")

    def _run_resource_tests(self, resource_handler: ResourceHandler) -> ResourceReport:
        """Run tests based on the resource type and config."""
        self._current_test_suite = get_test_suite(
            resource_handler, self.handler_storage
        )
        test_runner = get_test_runner()
        is_success, test_result = run_test_suite(test_runner, self._current_test_suite)
        self._current_test_suite = None

        return ResourceReport(
            resource_handler.name,
            resource_handler.conf.device_ip,
            resource_handler.device_type,
            resource_handler.family,
            is_success,
            test_result,
        )
