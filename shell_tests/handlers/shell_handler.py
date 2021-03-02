from typing import Optional

from cloudshell.rest.exceptions import ShellNotFoundException

from shell_tests.configs import ShellConfig
from shell_tests.handlers.cs_handler import CloudShellHandler
from shell_tests.handlers.smb_handler import CloudShellSmbHandler
from shell_tests.helpers.logger import logger
from shell_tests.helpers.shell_helpers import (
    get_resource_model_from_shell_definition,
    get_shell_name_from_shell_definition,
)


class ShellHandler:
    def __init__(
        self,
        conf: ShellConfig,
        cs_handler: CloudShellHandler,
        cs_smb_handler: Optional[CloudShellSmbHandler],
    ):
        self.conf = conf
        self.model = get_resource_model_from_shell_definition(self.conf.path)
        self.cs_shell_name = get_shell_name_from_shell_definition(self.conf.path)
        self._cs_handler = cs_handler
        self._cs_smb_handler = cs_smb_handler

    @classmethod
    def create(
        cls,
        conf: ShellConfig,
        cs_handler: CloudShellHandler,
        cs_smb_handler: Optional[CloudShellSmbHandler] = None,
    ) -> "ShellHandler":
        handler = cls(conf, cs_handler, cs_smb_handler)
        handler.prepare()
        return handler

    def install_shell(self):
        """Install the Shell."""
        self._cs_handler.install_shell(self.conf.path)

    def _store_extra_files(self):
        err_msg_smb_tmpl = (
            f"There are {{}} for a Shell {self.conf.name} but SMB Handler isn't set up"
        )
        if self._cs_smb_handler and self.conf.dependencies_path:
            self._cs_smb_handler.add_dependencies_to_offline_pypi(
                self.conf.dependencies_path
            )
        elif not self._cs_smb_handler and self.conf.dependencies_path:
            logger.warning(err_msg_smb_tmpl.format("dependecies file"))
        if self._cs_smb_handler and self.conf.extra_standards_paths:
            self._cs_smb_handler.add_extra_standards(self.conf.extra_standards_paths)
        elif not self._cs_smb_handler and self.conf.extra_standards_paths:
            logger.warning(err_msg_smb_tmpl.format("extra cs standards"))

    def prepare(self):
        logger.info(f"Start preparing the Shell {self.model}")
        try:
            self._store_extra_files()
            self.install_shell()
        except Exception as e:
            self.finish()
            raise e
        logger.debug("The Shell prepared")

    def finish(self):
        """Delete the Shell and clear Offline PyPI."""
        try:
            self._cs_handler.remove_shell(self.cs_shell_name)
        except ShellNotFoundException:
            pass
        except Exception as e:
            if "This shell is used" not in str(e):
                raise e
        if self.conf.dependencies_path and self._cs_smb_handler:
            # todo remove only added packages
            # todo remove added standards
            self._cs_smb_handler.clear_offline_pypi()
