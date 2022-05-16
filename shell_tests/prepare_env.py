from shell_tests.configs import MainConfig
from shell_tests.handlers.cs_handler import CloudShellHandler
from shell_tests.handlers.do_handler import DoHandler
from shell_tests.helpers.app_helpers import create_apps, create_blueprints
from shell_tests.helpers.check_resource_is_alive import check_all_resources_is_alive
from shell_tests.helpers.handler_storage import HandlerStorage
from shell_tests.helpers.logger import logger


class AutomatedPrepareEnv:
    def __init__(self, conf: MainConfig):
        self._conf = conf

    def run(self):
        check_all_resources_is_alive(self._conf)
        if self._conf.do_conf:
            DoHandler(self._conf).prepare()

        cs_handler = CloudShellHandler(self._conf.cs_conf)
        handler_storage = HandlerStorage(cs_handler, self._conf)

        # create resources on CS
        _ = handler_storage.resource_handlers
        for rh in handler_storage.resource_handlers:
            rh.autoload()

        create_apps(self._conf, handler_storage)
        create_blueprints(self._conf, handler_storage)

        # create sandboxes on CS
        _ = handler_storage.sandbox_handlers

        cs_url = f"http://{self._conf.cs_conf.host}"
        logger.info(f"The environment is prepared. CS url - {cs_url}")
