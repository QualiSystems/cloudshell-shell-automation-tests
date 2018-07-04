class ResourceReport(object):
    def __init__(self, resource_name, device_ip, device_type, is_success, test_result):
        self.name = resource_name
        self.ip = device_ip
        self.device_type = device_type
        self.is_success = is_success
        self.test_result = test_result


class Reporting(object):
    def __init__(self, shell_name):
        self.shell_name = shell_name
        self.resources_report = []  # type: list[ResourceReport]

    @property
    def is_success(self):
        return all(report.is_success for report in self.resources_report)

    def add_resource_report(self, resource_name, device_ip, device_type, is_success, test_result):
        self.resources_report.append(
            ResourceReport(resource_name, device_ip, device_type, is_success, test_result)
        )

    def get_result(self):
        results = []

        for report in self.resources_report:
            success_str = 'successful' if report.is_success else 'unsuccessful'
            results.append(
                'Resource name: {}, IP: {}, Type: {}\n'
                'Test for device was {}\n'
                '{}'.format(
                    report.name, report.ip, report.device_type, success_str, report.test_result)
            )

        return '\n\n'.join(results)
