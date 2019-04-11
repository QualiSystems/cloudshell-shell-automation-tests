from collections import OrderedDict
from itertools import chain

from shell_tests.blueprint_handler import BlueprintHandler
from shell_tests.configs import CloudShellConfig
from shell_tests.cs_handler import CloudShellHandler
from shell_tests.do_handler import DoHandler
from shell_tests.errors import ResourceIsNotAliveError, CSIsNotAliveError
from shell_tests.ftp_handler import FTPHandler
from shell_tests.helpers import is_host_alive, enter_stacks, wait_for_end_threads
from shell_tests.report_result import Reporting
from shell_tests.resource_handler import ResourceHandler, ServiceHandler
from shell_tests.run_tests_for_sandbox import RunTestsForSandbox
from shell_tests.sandbox_handler import SandboxHandler
from shell_tests.shell_handler import ShellHandler


class AutomatedTestsRunner(object):

    def __init__(self, conf, logger):
        """Create CloudShell on Do and run tests.

        :type conf: shell_tests.configs.MainConfig
        :param logger: logging.Logger
        """
        self.conf = conf
        self.logger = logger

        self._do_handler = None

    @property
    def do_handler(self):
        if self._do_handler is None and self.conf.do_conf:
            cs_handler = CloudShellHandler.from_conf(self.conf.do_conf, self.logger)
            self._do_handler = DoHandler(cs_handler, self.logger)
        return self._do_handler

    def create_cloudshell_on_do(self):
        """Create CloudShell instance on Do.

        :rtype: CloudShellConfig
        """
        cs_config = CloudShellConfig(
            *self.do_handler.get_new_cloudshell(
                self.conf.do_conf.cs_version, self.conf.do_conf.cs_specific_version)
        )
        return cs_config

    def get_run_tests_in_cloudshell(self):
        if not self.conf.do_conf:
            return RunTestsInCloudShell(self.conf, self.logger)

        error = None
        attempts = 5

        while attempts:
            attempts -= 1

            try:
                self.conf.cs_conf = self.create_cloudshell_on_do()
                run_tests_inst = RunTestsInCloudShell(self.conf, self.logger)
            except CSIsNotAliveError as error:
                pass  # try to recreate CS
            else:
                error = None
                return run_tests_inst
            finally:
                if error or self.conf.do_conf.delete_cs:
                    self.do_handler.end_reservation()

        if not attempts and error:
            raise error

    def run(self):
        """Create CloudShell, prepare, and run tests for all resources.

        :rtype: Reporting"""
        self.check_all_resources_is_alive()

        run_tests_inst = self.get_run_tests_in_cloudshell()
        try:
            return run_tests_inst.run()
        finally:
            if self.conf.do_conf and self.conf.do_conf.delete_cs:
                self.do_handler.end_reservation()

    def check_all_resources_is_alive(self):
        resources_to_check = {
            resource.name: resource.device_ip
            for resource in self.conf.resources_conf.values()
            if resource.device_ip
        }
        if self.conf.ftp_conf:
            resources_to_check['FTP'] = self.conf.ftp_conf.host
        if self.conf.do_conf:
            resources_to_check['Do'] = self.conf.do_conf.host
        else:
            resources_to_check['CloudShell'] = self.conf.cs_conf.host

        for name, host in resources_to_check.iteritems():
            if not is_host_alive(host):
                raise ResourceIsNotAliveError('{} ({}) is not alive, check it'.format(name, host))


class RunTestsInCloudShell(object):
    def __init__(self, main_conf, logger):
        """Run tests in CloudShell based on config.

        :type main_conf: shell_tests.configs.MainConfig
        :type logger: logging.Logger
        """
        self.main_conf = main_conf
        self.logger = logger

        self.cs_handler = CloudShellHandler.from_conf(main_conf.cs_conf, logger)
        # check CS is alive
        try:
            self.cs_handler.api
        except IOError:
            self._smb_handler = None
            self.logger.warning('CloudShell {} is not alive'.format(self.cs_handler.host))
            raise CSIsNotAliveError

        self.reporting = Reporting()
        self.ftp_handler = FTPHandler.from_conf(self.main_conf.ftp_conf, logger)
        self.shell_handlers = OrderedDict(
            (shell_conf.name, ShellHandler.from_conf(shell_conf, self.cs_handler, self.logger))
            for shell_conf in self.main_conf.shells_conf.values()
        )
        self.blueprint_handlers = OrderedDict(
            (conf.name, BlueprintHandler.from_conf(conf, self.cs_handler, self.logger))
            for conf in self.main_conf.blueprints_conf.values()
        )
        self.resource_handlers = OrderedDict(
            (
                conf.name,
                ResourceHandler.from_conf(
                    conf,
                    self.cs_handler,
                    self.shell_handlers.get(conf.shell_name),
                    logger,
                ),
            )
            for conf in self.main_conf.resources_conf.values()
        )
        self.service_handlers = OrderedDict(
            (
                conf.name,
                ServiceHandler.from_conf(
                    conf,
                    self.cs_handler,
                    self.shell_handlers.get(conf.shell_name),
                    logger,
                ),
            )
            for conf in self.main_conf.services_conf.values()
        )

    def run_tests_for_sandboxes(self):
        """Run tests for sandboxes."""
        threads = [
            RunTestsForSandbox(
                self._create_sandbox_handler(sandbox_conf),
                self.logger,
                self.reporting,
            )
            for sandbox_conf in self.main_conf.sandboxes_conf.values()
        ]

        for thread in threads:
            thread.start()

        try:
            wait_for_end_threads(threads)
        except KeyboardInterrupt:
            for thread in threads:
                thread.stop()
            wait_for_end_threads(threads)
            raise

    def _create_sandbox_handler(self, sandbox_conf):
        """Create the Sandbox Handler.

        :type sandbox_conf: shell_tests.configs.SandboxConfig
        """
        resource_handlers = map(self.resource_handlers.get, sandbox_conf.resource_names)
        service_handlers = map(self.service_handlers.get, sandbox_conf.service_names)
        return SandboxHandler.from_conf(
            sandbox_conf,
            resource_handlers,
            service_handlers,
            self.cs_handler,
            self.shell_handlers,
            self.ftp_handler,
            self.logger,
        )

    def run(self):
        """Install Shells and run tests for sandboxes.

        :rtype: Reporting
        """
        stacks = chain(
            self.shell_handlers.values(),
            self.blueprint_handlers.values(),
            self.resource_handlers.values(),
            self.service_handlers.values(),
        )
        with enter_stacks(stacks):
            self.run_tests_for_sandboxes()

        self.cs_handler.download_logs()
        return self.reporting
