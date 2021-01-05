import platform
import subprocess

from shell_tests.configs import MainConfig
from shell_tests.errors import ResourceIsNotAliveError


def _is_host_alive(host: str) -> bool:
    ping_count_str = "n" if platform.system().lower() == "windows" else "c"
    cmd = f"ping -{ping_count_str} 1 {host}"
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
        resources_to_check["FTP"] = conf.ftp_conf.netloc
    if conf.scp_conf:
        resources_to_check["SCP"] = conf.scp_conf.netloc
    if conf.tftp_conf:
        resources_to_check["TFTP"] = conf.tftp_conf.netloc
    if conf.do_conf:
        resources_to_check["Do"] = conf.do_conf.host
    else:
        resources_to_check["CloudShell"] = conf.cs_conf.host

    for name, host in resources_to_check.items():
        if not _is_host_alive(host):
            raise ResourceIsNotAliveError(f"{name} ({host}) is not alive, check it")
