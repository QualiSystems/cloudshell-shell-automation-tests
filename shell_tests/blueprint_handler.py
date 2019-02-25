import os

from shell_tests.helpers import is_url, download_file, call_exit_func_on_exc


class BlueprintHandler(object):
    def __init__(self, name, path, cs_handler, logger):
        """Blueprint Handler that cteates Blueprint on cloudshell.

        :type name: str
        :type path: str
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type logger: logging.Logger
        """
        self.name = name
        self.logger = logger
        self.downloaded_files = []
        self.cs_handler = cs_handler

        self.path = self.download_if_url(path)

    @classmethod
    def from_conf(cls, conf, cs_handler, logger):
        """Create Blueprint Handler from the config.

        :type conf: shell_tests.configs.BlueprintConfig
        :type cs_handler: shell_tests.cs_handler.CloudShellHandler
        :type logger: logging.Logger
        """
        return cls(
            conf.name,
            conf.path,
            cs_handler,
            logger,
        )

    def download_if_url(self, path):
        """Download file if it is a URL.

        :type path: str
        """
        if path and is_url(path):
            self.logger.info('Downloading the file from url {}'.format(path))
            path = download_file(path)
            self.downloaded_files.append(path)

        return path

    def deleting_downloaded_files(self):
        """Delete downloaded files."""
        for path in self.downloaded_files:
            self.logger.info('Deleting the downloaded file {}'.format(path))
            os.remove(path)

    def import_blueprint(self):
        self.cs_handler.import_package(self.path)

    @call_exit_func_on_exc
    def __enter__(self):
        self.import_blueprint()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.deleting_downloaded_files()
        return False
