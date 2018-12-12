from shell_tests.configs import ShellConfig, CloudShellConfig
from shell_tests.cs_handler import CloudShellHandler
from shell_tests.do_handler import DoHandler
from shell_tests.errors import ResourceIsNotAliveError, CSIsNotAliveError
from shell_tests.helpers import is_host_alive
from shell_tests.report_result import Reporting
from shell_tests.run_tests_for_resource import RunTestsForResource
from shell_tests.shell_handler import ShellHandler
from shell_tests.smb_handler import SMB


class TestsRunner(object):
    CLOUDSHELL_SERVER_NAME = 'User-PC'

    def __init__(self, conf, logger):
        """Decide for tests need to run and run it

        :param ShellConfig conf:
        :param logging.Logger logger:
        """

        self.conf = conf
        self.logger = logger

        self._do_handler = None
        self._smb_handler = None

    @property
    def do_handler(self):
        if self._do_handler is None and self.conf.do:
            cs_handler = CloudShellHandler(
                self.conf.do.host,
                self.conf.do.user,
                self.conf.do.password,
                self.logger,
                self.conf.do.domain,
            )
            self._do_handler = DoHandler(cs_handler, self.logger)

        return self._do_handler

    @property
    def smb_handler(self):
        if self._smb_handler is None and self.conf.cs.os_user:
            self._smb_handler = SMB(
                self.conf.cs.os_user,
                self.conf.cs.os_password,
                self.conf.cs.host,
                self.CLOUDSHELL_SERVER_NAME,
                self.logger,
            )

        return self._smb_handler

    def create_cloudshell_on_do(self):
        """Create CloudShell instance on Do."""
        cs_config = CloudShellConfig(
            *self.do_handler.get_new_cloudshell(self.conf.do.cs_version)
        )
        self.conf.cs = cs_config

    def delete_cloudshell_on_do(self):
        """Ends CloudShell reservation on Do"""

        if self.do_handler:
            self.do_handler.end_reservation()

    def get_cs_handler(self):
        cs_handler = CloudShellHandler(
            self.conf.cs.host,
            self.conf.cs.user,
            self.conf.cs.password,
            self.logger,
            self.conf.cs.domain,
            self.smb_handler,
        )

        try:
            api = cs_handler.api
        except IOError:
            self._smb_handler = None
            raise CSIsNotAliveError
        else:
            del api

        return cs_handler

    def run_tests(self, cs_handler):
        """Run tests in CloudShell for Shell on one or several devices

        :param CloudShellHandler cs_handler:
        :rtype: Reporting
        """
        report = Reporting(self.conf.shell_name)

        dut_shell_handler = ShellHandler(
            cs_handler,
            self.conf.dut_shell_path,
            self.conf.dut_dependencies_path if self.conf.dependencies_path else None,
            self.logger,
        )
        self.conf.dut_shell_path = dut_shell_handler.shell_path

        shell_handler = ShellHandler(
            cs_handler,
            self.conf.shell_path,
            self.conf.dependencies_path,
            self.logger,
        )
        self.conf.shell_path = shell_handler.shell_path

        with shell_handler, dut_shell_handler:
            threads = [
                RunTestsForResource(
                    cs_handler, self.conf, resource_conf, shell_handler, self.logger, report)
                for resource_conf in self.conf.resources
            ]

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

        cs_handler.download_logs()
        return report

    def run(self):
        self.check_all_resources_is_alive()

        report = error = None
        attempts = 5

        while report is None and attempts:
            attempts -= 1

            try:
                if self.conf.do:
                    self.create_cloudshell_on_do()
                cs_handler = self.get_cs_handler()
            except CSIsNotAliveError as error:
                pass  # try to recreate CS
            else:
                report = self.run_tests(cs_handler)
            finally:
                if self.conf.do and self.conf.do.delete_cs:
                    self.delete_cloudshell_on_do()

        if not attempts and error:
            raise error

        return report

    def check_all_resources_is_alive(self):
        resources_to_check = {
            resource.resource_name: resource.device_ip for resource in self.conf.resources
            if resource.device_ip
        }
        resources_to_check['FTP'] = self.conf.ftp.host
        if self.conf.do:
            resources_to_check['Do'] = self.conf.do.host
        else:
            resources_to_check['CloudShell'] = self.conf.cs.host

        for name, host in resources_to_check.iteritems():
            if not is_host_alive(host):
                raise ResourceIsNotAliveError('{} ({}) is not alive, check it'.format(name, host))
