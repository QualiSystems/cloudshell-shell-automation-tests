class SandboxReport(object):
    def __init__(self, sandbox_name, is_success, test_result):
        self.name = sandbox_name
        self.sandbox_is_success = is_success
        self.test_result = test_result
        self.resources_reports = []  # type: list[ResourceReport]

    @property
    def is_success(self):
        return all(r.is_success for r in self.resources_reports) and self.sandbox_is_success

    def __str__(self):
        sandbox_tests_result = ''
        if self.test_result:
            success_str = 'successful' if self.sandbox_is_success else 'unsuccessful'
            sandbox_tests_result = ('Sandbox name: {0.name}\nTests for sandbox was {1}\n'
                                    '{0.test_result}\n\n'.format(self, success_str))

        resources_tests_result = '\n\n'.join(map(str, self.resources_reports))

        success_str = 'successful' if self.is_success else 'unsuccessful'
        result = 'Sandbox name: {}\nTests for sandbox and resources was {}\n\n{}{}'.format(
            self.name, success_str, sandbox_tests_result, resources_tests_result)

        return result


class ResourceReport(object):
    def __init__(self, resource_name, device_ip, device_type, family, is_success, test_result):
        self.name = resource_name
        self.ip = device_ip
        self.device_type = device_type
        self.family = family
        self.is_success = is_success
        self.test_result = test_result

    def __str__(self):
        success_str = 'successful' if self.is_success else 'unsuccessful'
        result = ('Resource name: {0.name}, IP: {0.ip}, Type: {0.device_type}, Family: {0.family}\n'
                  'Test for the device was {1}\n'
                  '{0.test_result}'.format(self, success_str))

        return result


class Reporting(object):
    def __init__(self):
        self.sandboxes_reports = []  # type: list[SandboxReport]

    @property
    def is_success(self):
        return all(sandbox.is_success for sandbox in self.sandboxes_reports)

    def __str__(self):
        join_str = '\n\n{}\n\n'.format('-' * 100)
        sandboxes_tests_result = join_str.join(map(str, self.sandboxes_reports))

        success_str = 'successful' if self.is_success else 'unsuccessful'
        result = 'Tests was {}\n\n{}'.format(success_str, sandboxes_tests_result)

        return result
