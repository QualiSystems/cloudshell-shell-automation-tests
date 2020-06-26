import pytest

from shell_tests.configs import MainConfig

from tests.base import CONFIGS_DIR


@pytest.fixture
def conf() -> MainConfig:
    path = CONFIGS_DIR / "test_tests_conf_in_shell_and_resource.yaml"
    return MainConfig.from_yaml(path)


def test_tests_config_shared_between_resource_and_shell(conf: MainConfig):
    for resource_conf in conf.resources_conf:
        shell_conf = next(
            iter(sc for sc in conf.shells_conf if sc.name == resource_conf.shell_name)
        )
        _expected_new_dict = {
            **shell_conf.tests_conf.expected_failures,
            **resource_conf.tests_conf.expected_failures,
        }
        assert resource_conf.tests_conf.expected_failures == _expected_new_dict, (
            "Resource expected failures is more important, but we also need to use "
            "expected failures from the Shell"
        )
        if resource_conf.name == "Cisco":
            assert (
                resource_conf.tests_conf.run_tests is True
            ), "Should use resource run tests if specified in config for the resource"
        else:
            assert (
                resource_conf.tests_conf.run_tests is False
            ), "Should use run_tests from Shell definition"
