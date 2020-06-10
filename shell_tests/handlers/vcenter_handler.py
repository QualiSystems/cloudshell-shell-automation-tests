import ssl
from functools import cached_property

import requests
from pyVim.connect import Disconnect, SmartConnect

from shell_tests.configs import VcenterConfig
from shell_tests.errors import BaseAutomationException


class VcenterError(BaseAutomationException):
    """Base vCenter Error."""


class VcenterHandler:
    def __init__(self, conf: VcenterConfig):
        self.conf = conf

    @cached_property
    def _si(self) -> SmartConnect:
        try:
            si = SmartConnect(
                host=self.conf.host, user=self.conf.user, pwd=self.conf.password
            )
        except ssl.SSLError:
            requests.packages.urllib3.disable_warnings()
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            ssl_context.verify_mode = ssl.CERT_NONE

            si = SmartConnect(
                host=self.conf.host,
                user=self.conf.user,
                pwd=self.conf.password,
                sslContext=ssl_context,
            )
        return si

    def _logout(self):
        Disconnect(self._si)
        del self._si

    def get_vm_by_uuid(self, vm_uuid: str):
        return self._si.content.searchIndex.FindByUuid(None, vm_uuid, True)

    def prepare(self):
        pass

    def finish(self):
        self._logout()
