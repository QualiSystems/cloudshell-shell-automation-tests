from pathlib import Path
from typing import Optional

from shell_tests.configs import MainConfig
from shell_tests.handlers.cs_handler import CloudShellHandler
from shell_tests.handlers.sandbox_handler import SandboxHandler
from shell_tests.helpers.check_resource_is_alive import check_all_resources_is_alive
from shell_tests.helpers.do_helpers import CSCreator
from shell_tests.helpers.handler_storage import HandlerStorage
from shell_tests.helpers.threads_helper import wait_for_end_threads
from shell_tests.report_result import Reporting
from shell_tests.run_tests_for_sandbox import RunTestsForSandbox


class AutomatedTestsRunner:
    def __init__(self, conf: MainConfig):
        """Create CloudShell on Do and run tests."""
        self.conf = conf
        self._do_sandbox_handler: Optional[SandboxHandler] = None

    def run(self) -> Reporting:
        """Create CloudShell, prepare, and run tests for all resources."""
        check_all_resources_is_alive(self.conf)
        do = None
        if self.conf.do_conf:
            do = CSCreator(self.conf)
            cs_handler = do.create_cloudshell()
        else:
            cs_handler = CloudShellHandler(self.conf.cs_conf)

        try:
            return self._run_cs_tests(cs_handler)
        finally:
            if do and self.conf.do_conf and self.conf.do_conf.delete_cs:
                do.finish()

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
