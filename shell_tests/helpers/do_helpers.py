import platform
import subprocess

from shell_tests.configs import (
    CloudShellConfig,
    DeploymentResourceConfig,
    DoConfig,
    MainConfig,
    SandboxConfig,
)
from shell_tests.errors import BaseAutomationException, ResourceIsNotAliveError
from shell_tests.handlers.cs_handler import CloudShellHandler
from shell_tests.handlers.resource_handler import DeploymentResourceHandler
from shell_tests.handlers.sandbox_handler import SandboxHandler
from shell_tests.helpers.logger import logger


def _is_host_alive(host: str) -> bool:
    ping_count_str = "n" if platform.system().lower() == "windows" else "c"
    cmd = "ping -{} 1 {}".format(ping_count_str, host)
    try:
        _ = subprocess.check_output(cmd, shell=True)
    except subprocess.CalledProcessError:
        return False
    return True


def check_all_resources_is_alive(conf: MainConfig):
    resources_to_check = {
        resource.name: resource.device_ip
        for resource in conf.resources_conf
        if resource.device_ip
    }
    if conf.ftp_conf:
        resources_to_check["FTP"] = conf.ftp_conf.host
    if conf.do_conf:
        resources_to_check["Do"] = conf.do_conf.host
    else:
        resources_to_check["CloudShell"] = conf.cs_conf.host

    for name, host in resources_to_check.items():
        if not _is_host_alive(host):
            raise ResourceIsNotAliveError(f"{name} ({host}) is not alive, check it")


def _find_topology_name_for_cloudshell(do: CloudShellHandler, version: str) -> str:
    cs_names = sorted(do.get_topologies_by_category("CloudShell"))
    for topology_name in cs_names:
        # 'Environments/CloudShell - Latest 8.3'
        if topology_name.split("/", 1)[-1] == version:
            return topology_name
    raise BaseAutomationException(f"CloudShell version {version} isn't exists")


def start_cs_sandbox(
    do_handler: CloudShellHandler, do_conf: DoConfig
) -> SandboxHandler:
    topology_name = _find_topology_name_for_cloudshell(do_handler, do_conf.cs_version)
    logger.debug(f"Creating CloudShell {topology_name}")
    conf = SandboxConfig(
        **{
            "Name": "auto tests",
            "Resources": [],
            "Blueprint Name": topology_name,
            "Specific Version": do_conf.cs_specific_version,
        }
    )
    return SandboxHandler.create(conf, do_handler)


def _get_cs_resource(
    sandbox_handler: SandboxHandler, version: str
) -> DeploymentResourceHandler:
    cs_deployed_resource_conf = DeploymentResourceConfig(
        **{"Name": "CloudShell", "Blueprint Name": version}
    )
    return DeploymentResourceHandler.create_from_conf(
        cs_deployed_resource_conf, sandbox_handler
    )


def _get_cs_config(resource_handler: DeploymentResourceHandler) -> CloudShellConfig:
    info = resource_handler.get_details()
    attrs = {attr.Name: attr.Value for attr in info.ResourceAttributes}
    data = {
        "Host": info.Address,
        "User": "admin",
        "Password": "admin",
        "OS User": attrs["OS Login"],
        "OS Password": attrs["OS Password"],
    }
    return CloudShellConfig(**data)


def get_cs_config(sandbox_handler: SandboxHandler, cs_version: str) -> CloudShellConfig:
    resource = _get_cs_resource(sandbox_handler, cs_version)
    return _get_cs_config(resource)
