import ssl

import requests
from pyVim.connect import SmartConnect, Disconnect

from shell_tests.errors import BaseAutomationException


class VcenterError(BaseAutomationException):
    """Base vCenter Error"""


class VcenterHandler(object):
    """vCenter Handler."""
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password

        self._si = None

    @classmethod
    def from_config(cls, config):
        """Create vCenter Handler from the config.

        :type config: shell_tests.configs.VcenterConfig
        """
        return cls(
            config.host,
            config.user,
            config.password,
        )

    @property
    def si(self):
        if self._si is None:
            raise VcenterError('You have to login first')
        return self._si

    def login(self):
        try:
            si = SmartConnect(
                host=self.host,
                user=self.user,
                pwd=self.password,
            )
        except ssl.SSLError:
            requests.packages.urllib3.disable_warnings()
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            ssl_context.verify_mode = ssl.CERT_NONE

            si = SmartConnect(
                host=self.host,
                user=self.user,
                pwd=self.password,
                sslContext=ssl_context,
            )

        self._si = si

    def logout(self):
        Disconnect(self.si)

    def __enter__(self):
        self.login()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._si:
            self.logout()
        return False

    def get_vm_by_uuid(self, vm_uuid):
        return self.si.content.searchIndex.FindByUuid(None, vm_uuid, True)
