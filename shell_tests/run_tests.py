from concurrent import futures as ft
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from threading import Event
from typing import Optional

from shell_tests.configs import MainConfig
from shell_tests.errors import BaseAutomationException
from shell_tests.handlers.cs_handler import CloudShellHandler
from shell_tests.handlers.do_handler import DoHandler
from shell_tests.handlers.sandbox_handler import SandboxHandler
from shell_tests.helpers.check_resource_is_alive import check_all_resources_is_alive
from shell_tests.helpers.handler_storage import HandlerStorage
from shell_tests.report_result import Reporting
from shell_tests.run_tests_for_sandbox import RunTestsForSandbox


class AutomatedTestsRunner:
    def __init__(self, conf: MainConfig):
        """Create CloudShell on Do and run tests."""
        self._conf = conf
        self._do_sandbox_handler: Optional[SandboxHandler] = None

    def run(self) -> Reporting:
        """Create CloudShell, prepare, and run tests for all resources."""
        check_all_resources_is_alive(self._conf)

        context = DoHandler(self._conf) if self._conf.do_conf else nullcontext()
        with context:
            cs_handler = CloudShellHandler(self._conf.cs_conf)
            return self._run_cs_tests(cs_handler)

    def _run_cs_tests(self, cs_handler: CloudShellHandler) -> Reporting:
        report = Reporting()
        stop_flag = Event()
        start_time = datetime.now()
        handler_storage = HandlerStorage(cs_handler, self._conf)
        run_tests_instances = {
            RunTestsForSandbox(sh, handler_storage, report, stop_flag)
            for sh in handler_storage.sandbox_handlers
        }

        with ft.ThreadPoolExecutor(5, thread_name_prefix="Sandbox-thread") as executor:
            futures = {executor.submit(rti.run) for rti in run_tests_instances}
            try:
                self._wait_for_futures(futures, stop_flag)
            except KeyboardInterrupt:
                stop_flag.set()
                self._wait_for_futures(futures, stop_flag)
                raise
            finally:
                handler_storage.cs_smb_handler.download_logs(
                    Path("cs_logs"),
                    start_time,
                    {sh.reservation_id for sh in handler_storage.sandbox_handlers},
                )
                handler_storage.finish()
        return report

    @staticmethod
    def _wait_for_futures(futures: set[ft.Future], stop_flag: Event):
        done, undone = ft.wait(futures, return_when=ft.FIRST_EXCEPTION)
        for f in done:
            if f.exception() is not None:
                stop_flag.set()
                ft.wait(futures)
        exceptions = set(filter(None, map(ft.Future.exception, futures)))
        if exceptions:
            emsg = f"Sandbox threads finished with exceptions: {exceptions}"
            raise BaseAutomationException(emsg)
