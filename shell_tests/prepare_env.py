from shell_tests.configs import MainConfig
from shell_tests.handlers.cs_handler import CloudShellHandler
from shell_tests.handlers.do_handler import DoHandler
from shell_tests.helpers.check_resource_is_alive import check_all_resources_is_alive
from shell_tests.helpers.handler_storage import HandlerStorage


class AutomatedPrepareEnv:
    def __init__(self, conf: MainConfig):
        self._conf = conf

    def run(self):
        check_all_resources_is_alive(self._conf)
        if self._conf.do_conf:
            DoHandler(self._conf).prepare()

        cs_handler = CloudShellHandler(self._conf.cs_conf)
        handler_storage = HandlerStorage(cs_handler, self._conf)
        _ = handler_storage.resource_handlers
        _ = handler_storage.sandbox_handlers
