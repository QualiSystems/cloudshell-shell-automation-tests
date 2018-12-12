from shell_tests.helpers import get_resource_family_and_model


class DutHandler(object):
    def __init__(self, cs_handler, shell_path, reservation_id, logger):
        """
        :param shell_tests.cs_handler.CloudShellHandler cs_handler:
        :param str shell_path:
        :param str reservation_id:
        :param logging.Logger logger:
        """

        self.cs_handler = cs_handler
        self.shell_path = shell_path
        self.reservation_id = reservation_id
        self.logger = logger

        self.name = 'DUT'
        self.downloaded_shell_file = False
        self.downloaded_dependencies_file = False
        self.resource_family, self.resource_model = get_resource_family_and_model(
            self.shell_path, self.logger)

    def create_and_add_to_reservation(self):
        self.logger.info('Adding DUT device to the reservation')
        self.name = self.cs_handler.create_resource(
            self.name,
            self.resource_family,
            self.resource_model,
            '127.0.0.1',
        )
        self.cs_handler.add_resource_to_reservation(self.reservation_id, self.name)
        self.cs_handler.resource_autoload(self.name)

    def __enter__(self):
        self.create_and_add_to_reservation()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
