from typing import Dict, List, Optional, TypeVar

from shell_tests.configs import MainConfig
from shell_tests.handlers.cs_handler import CloudShellHandler
from shell_tests.handlers.ftp_handler import FTPHandler
from shell_tests.handlers.resource_handler import ResourceHandler
from shell_tests.handlers.sandbox_handler import SandboxHandler
from shell_tests.handlers.scp_handler import SCPHandler
from shell_tests.handlers.shell_handler import ShellHandler
from shell_tests.handlers.smb_handler import CloudShellSmbHandler
from shell_tests.handlers.tftp_handler import TFTPHandler
from shell_tests.handlers.vcenter_handler import VcenterHandler

Handler = TypeVar("Handler")


def _get_handlers_dict(handlers_lst: List[Handler]) -> Dict[str, Handler]:
    return {h.conf.name: h for h in handlers_lst}


class HandlerStorage:
    def __init__(
        self, cs_handler: CloudShellHandler, conf: MainConfig,
    ):
        self.cs_handler = cs_handler
        self.conf = conf

        self._cs_smb_handler = None
        self._ftp_handler = None
        self._scp_handler = None
        self._tftp_handler = None
        self._vcenter_handler = None
        self._shell_handlers = None
        self._resource_handlers = None
        self._sandbox_handlers = None

    @property
    def cs_smb_handler(self) -> Optional[CloudShellSmbHandler]:
        if (
            self._cs_smb_handler is None
            and self.conf.cs_conf.os_user
            and self.conf.cs_conf.os_password
        ):
            self._cs_smb_handler = CloudShellSmbHandler(self.conf.cs_conf)
        return self._cs_smb_handler

    @property
    def ftp_handler(self) -> Optional[FTPHandler]:
        if self._ftp_handler is None and self.conf.ftp_conf:
            self._ftp_handler = FTPHandler(self.conf.ftp_conf)
        return self._ftp_handler

    @property
    def scp_handler(self) -> Optional[SCPHandler]:
        if self._scp_handler is None and self.conf.scp_conf:
            self._scp_handler = SCPHandler(self.conf.scp_conf)
        return self._scp_handler

    @property
    def tftp_handler(self) -> Optional[TFTPHandler]:
        if self._tftp_handler is None and self.conf.tftp_conf:
            self._tftp_handler = TFTPHandler(self.conf.tftp_conf)
        return self._tftp_handler

    @property
    def vcenter_handler(self) -> Optional[VcenterHandler]:
        if self._vcenter_handler is None and self.conf.vcenter_conf:
            self._vcenter_handler = VcenterHandler(self.conf.vcenter_conf)
        return self._vcenter_handler

    @property
    def shell_handlers(self) -> List[ShellHandler]:
        if self._shell_handlers is None:
            self._shell_handlers = []
            try:
                for conf in self.conf.shells_conf:
                    shell = ShellHandler.create(
                        conf, self.cs_handler, self.cs_smb_handler
                    )
                    self._shell_handlers.append(shell)
            except BaseException as e:
                self.finish()
                raise e
        return self._shell_handlers

    @property
    def shell_handlers_dict(self) -> Dict[str, ShellHandler]:
        return _get_handlers_dict(self.shell_handlers)

    @property
    def resource_handlers(self) -> List[ResourceHandler]:
        if self._resource_handlers is None:
            self._resource_handlers = []
            try:
                for conf in self.conf.resources_conf:
                    shell = self.shell_handlers_dict[conf.shell_name]
                    resource = ResourceHandler.create(conf, self.cs_handler, shell)
                    self._resource_handlers.append(resource)
            except BaseException as e:
                self.finish()
                raise e
        return self._resource_handlers

    @property
    def resource_handlers_dict(self) -> Dict[str, ResourceHandler]:
        return _get_handlers_dict(self.resource_handlers)

    @property
    def sandbox_handlers(self) -> List[SandboxHandler]:
        if self._sandbox_handlers is None:
            self._sandbox_handlers = []
            try:
                for conf in self.conf.sandboxes_conf:
                    sandbox = SandboxHandler.create(conf, self.cs_handler)
                    self._sandbox_handlers.append(sandbox)
            except BaseException as e:
                self.finish()
                raise e
        return self._sandbox_handlers

    @property
    def sandbox_handler_dict(self) -> Dict[str, SandboxHandler]:
        return _get_handlers_dict(self.sandbox_handlers)

    def finish(self):
        if self._sandbox_handlers is not None:
            for sh in self.sandbox_handlers:
                sh.finish()
        if self._resource_handlers is not None:
            for rh in self.resource_handlers:
                rh.finish()
        if self._shell_handlers is not None:
            for sh in self.shell_handlers:
                sh.finish()
        if self._vcenter_handler is not None:
            self.vcenter_handler.finish()
