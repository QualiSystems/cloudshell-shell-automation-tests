import threading
from concurrent import futures as ft
from functools import cached_property
from threading import Event

from shell_tests.handlers.resource_handler import ResourceHandler
from shell_tests.handlers.sandbox_handler import SandboxHandler
from shell_tests.helpers.handler_storage import HandlerStorage
from shell_tests.helpers.logger import logger
from shell_tests.helpers.tests_helpers import (
    get_test_runner,
    get_test_suite,
    run_test_suite,
)
from shell_tests.helpers.threads_helper import set_thread_name_with_suffix
from shell_tests.report_result import Reporting, ResourceReport, SandboxReport


class RunTestsForSandbox:
    REPORT_LOCK = threading.Lock()

    def __init__(
        self,
        sandbox_handler: SandboxHandler,
        handler_storage: HandlerStorage,
        reporting: Reporting,
        stop_flag: Event,
    ):
        """Run Tests based on the Sandbox."""
        self.sandbox_handler = sandbox_handler
        self.handler_storage = handler_storage
        self.reporting = reporting
        self._stop_flag = stop_flag

    @cached_property
    def resource_handlers(self) -> list[ResourceHandler]:
        handlers = [
            self.handler_storage.resource_handlers_dict[name]
            for name in self.sandbox_handler.conf.resource_names
        ]
        for handler in handlers:
            if handler.conf.tests_conf.run_tests:
                # do not add resources that would be used only for connectivity
                self.sandbox_handler.add_resource_to_reservation(handler)
        return handlers

    def _is_stop_set(self):
        if self._stop_flag.is_set():
            raise KeyboardInterrupt

    def run(self):
        """Run tests for the Sandbox and resources."""
        set_thread_name_with_suffix(self.sandbox_handler.conf.name)
        self._is_stop_set()
        sandbox_report = self._run_sandbox_tests()

        with ft.ThreadPoolExecutor(thread_name_prefix="[Resource tests]") as executor:
            futures = {
                executor.submit(self._execute_resource_tests, rh, sandbox_report)
                for rh in self.resource_handlers
            }
            ft.wait(futures)
            for future in futures:
                future.result()

        with self.REPORT_LOCK:
            self.reporting.sandboxes_reports.append(sandbox_report)

    def _run_sandbox_tests(self) -> SandboxReport:
        return SandboxReport(self.sandbox_handler.conf.name, True, "")

    def _execute_resource_tests(
        self, resource_handler: ResourceHandler, sandbox_report: SandboxReport
    ):
        thread_name = f"({self.sandbox_handler.conf.name})-{resource_handler.name}"
        set_thread_name_with_suffix(thread_name)
        self._is_stop_set()
        resource_handler.run_resource_commands(resource_handler.conf.setup_commands)
        self._is_stop_set()
        if resource_handler.conf.tests_conf.run_tests:
            resource_report = self._run_resource_tests(resource_handler)
            with self.REPORT_LOCK:
                sandbox_report.resources_reports.append(resource_report)
            self._is_stop_set()
            resource_handler.run_resource_commands(
                resource_handler.conf.teardown_commands
            )
        else:
            try:
                resource_handler.autoload_if_needed()
            except Exception as e:
                emsg = f"Cannot autoload {resource_handler.conf.name}\n{e}"
                logger.exception(emsg)

    def _run_resource_tests(self, resource_handler: ResourceHandler) -> ResourceReport:
        """Run tests based on the resource type and config."""
        test_suite = get_test_suite(
            self._stop_flag, resource_handler, self.handler_storage
        )
        test_runner = get_test_runner()
        is_success, test_result = run_test_suite(test_runner, test_suite)

        return ResourceReport(
            resource_handler.name,
            resource_handler.conf.device_ip,
            resource_handler.device_type,
            resource_handler.family,
            is_success,
            test_result,
        )
