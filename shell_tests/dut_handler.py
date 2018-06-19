import os

from shell_tests.helpers import get_resource_family_and_model, is_url, download_file


class DutHandler(object):
    def __init__(self, cs_handler, reservation_id, shell_path, logger):
        """
        :param shell_tests.cs_handler.CloudShellHandler cs_handler:
        :param str reservation_id:
        :param str shell_path:
        :param logging.Logger logger:
        """

        self.cs_handler = cs_handler
        self.reservation_id = reservation_id
        self.shell_path = shell_path
        self.logger = logger
        self.name = 'DUT'
        self.downloaded_shell_file = False

    def install_shell(self):
        if is_url(self.shell_path):
            self.logger.info('Downloading the DUT Shell from {}'.format(self.shell_path))
            self.shell_path = download_file(self.shell_path)
            self.downloaded_shell_file = True
        self.cs_handler.install_shell(self.shell_path)

    def create_and_add_to_reservation(self):
        self.logger.info('Adding DUT device to the reservation')
        self.install_shell()
        family, model = get_resource_family_and_model(self.shell_path, self.logger)
        self.name = self.cs_handler.create_resource(
            self.name,
            family,
            model,
            '127.0.0.1',
        )
        self.cs_handler.add_resource_to_reservation(self.reservation_id, self.name)
        self.cs_handler.resource_autoload(self.name)

    def delete_resource(self):
        self.cs_handler.delete_resource(self.name)

        if self.downloaded_shell_file:
            self.logger.debug('Deleting the DUT Shell file')
            os.remove(self.shell_path)

    def __enter__(self):
        self.create_and_add_to_reservation()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delete_resource()
        return False
