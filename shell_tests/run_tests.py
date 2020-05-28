from functools import cached_property
from pathlib import Path
from typing import Optional

from shell_tests.configs import MainConfig
from shell_tests.errors import CSIsNotAliveError
from shell_tests.handlers.cs_handler import CloudShellHandler
from shell_tests.handlers.sandbox_handler import SandboxHandler
from shell_tests.helpers.do_helpers import (
    check_all_resources_is_alive,
    get_cs_config,
    start_cs_sandbox,
)
from shell_tests.helpers.handler_storage import HandlerStorage
from shell_tests.helpers.logger import logger
from shell_tests.helpers.threads_helper import wait_for_end_threads
from shell_tests.report_result import Reporting
from shell_tests.run_tests_for_sandbox import RunTestsForSandbox


class AutomatedTestsRunner:
    def __init__(self, conf: MainConfig):
        """Create CloudShell on Do and run tests."""
        self.conf = conf
        self._do_sandbox_handler: Optional[SandboxHandler] = None

    @cached_property
    def do_handler(self):
        return CloudShellHandler(self.conf.do_conf)

    def _create_cloudshell_on_do(self) -> CloudShellHandler:
        for _ in range(5):
            self._do_sandbox_handler = start_cs_sandbox(
                self.do_handler, self.conf.do_conf
            )
            try:
                conf = get_cs_config(
                    self._do_sandbox_handler, self.conf.do_conf.cs_version
                )
                self.conf.cs_conf = conf
                cs_handler = CloudShellHandler(conf)
                cs_handler.wait_for_cs_is_started()
            except CSIsNotAliveError:
                logger.exception("The CS is not started")
                self._do_sandbox_handler.end_reservation()
            except Exception as e:
                self._do_sandbox_handler.end_reservation()
                raise e
            else:
                return cs_handler
        else:
            raise CSIsNotAliveError("All 5 CloudShells are not started")

    def run(self) -> Reporting:
        """Create CloudShell, prepare, and run tests for all resources."""
        check_all_resources_is_alive(self.conf)
        if self.conf.do_conf:
            cs_handler = self._create_cloudshell_on_do()
        else:
            cs_handler = CloudShellHandler(self.conf.cs_conf)

        try:
            return self._run_cs_tests(cs_handler)
        finally:
            if self._do_sandbox_handler and self.conf.do_conf.delete_cs:
                logger.info("Deleting CS on Do")
                self._do_sandbox_handler.end_reservation()

    def _run_cs_tests(self, cs_handler: CloudShellHandler) -> Reporting:
        report = Reporting()
        handler_storage = HandlerStorage(cs_handler, self.conf)
        threads = [
            RunTestsForSandbox(sandbox_handler, handler_storage, report)
            for sandbox_handler in handler_storage.sandbox_handlers
        ]
        try:
            for thread in threads:
                thread.start()
            wait_for_end_threads(threads)
        except KeyboardInterrupt:
            for thread in threads:
                thread.stop()
            wait_for_end_threads(threads)
            raise
        finally:
            handler_storage.cs_smb_handler.download_logs(Path("cs_logs"))
            handler_storage.finish()
        return report
