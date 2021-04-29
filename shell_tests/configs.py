from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, validator

from shell_tests.helpers.config_helpers import str_version_to_tuple
from shell_tests.helpers.download_files_helper import DownloadFile

MIN_COMPATIBLE_CONF_VER = "0.13"
MAX_COMPATIBLE_CONF_VER = "0.16"


class CloudShellConfig(BaseModel):
    host: str = Field(..., alias="Host")
    user: str = Field(..., alias="User")
    password: str = Field(..., alias="Password")
    os_user: str = Field("", alias="OS User")
    os_password: str = Field("", alias="OS Password")
    domain: str = Field("Global", alias="Domain")


class NetworkingAppConf(BaseModel):
    name: str = Field(..., alias="Name")
    blueprint_name: str = Field(..., alias="Blueprint Name")


class CSonDoConfig(BaseModel):
    cs_version: str = Field("CloudShell 9.3 GA - IL", alias="CS Version")
    delete_cs: bool = Field(True, alias="Delete CS")
    cs_specific_version: str = Field("", alias="CS Specific Version")


class DoConfig(CloudShellConfig):
    cs_on_do_conf: Optional[CSonDoConfig] = Field(None, alias="CloudShell")
    networking_apps: list[NetworkingAppConf] = Field([], alias="Networking Apps")


class TestsConfig(BaseModel):
    expected_failures: dict[str, str] = Field({}, alias="Expected failures")
    run_tests: bool = Field(True, alias="Run Tests")
    original_run_tests: Optional[bool] = Field(None, alias="Run Tests")

    def __iadd__(self, other: "TestsConfig"):
        if not isinstance(other, TestsConfig):
            raise NotImplementedError("You can add only TestsConfig")
        self.expected_failures = {**other.expected_failures, **self.expected_failures}
        if self.original_run_tests is not None:
            self.run_tests = self.original_run_tests
        elif other.original_run_tests is not None:
            self.run_tests = other.original_run_tests
        return self


class AdditionalPort(BaseModel):
    name: str = Field(..., alias="Name")


class ResourceCommandMode(Enum):
    ENABLE = "ENABLE"
    CONFIG = "CONFIG"


class ResourceCommand(BaseModel):
    command: str
    mode: ResourceCommandMode


class ResourceConfig(BaseModel):
    name: str = Field(..., alias="Name")
    shell_name: str = Field(..., alias="Shell Name")
    device_ip: Optional[str] = Field(None, alias="Device IP")
    attributes: dict[str, str] = Field({}, alias="Attributes")
    children_attributes: dict[str, dict[str, str]] = Field(
        {}, alias="Children Attributes"
    )
    tests_conf: TestsConfig = Field(TestsConfig(), alias="Tests")
    is_first_gen: bool = Field(False, alias="First Gen")
    networking_app_name: Optional[str] = Field(None, alias="Networking App")
    additional_ports: list[AdditionalPort] = Field([], alias="Additional Ports")
    setup_commands: list[ResourceCommand] = Field([], alias="Setup Commands")
    teardown_commands: list[ResourceCommand] = Field([], alias="Teardown Commands")

    @validator("setup_commands", "teardown_commands", each_item=True, pre=True)
    def _parse_commands(cls, v):
        if isinstance(v, dict):
            if len(v) != 1:
                raise ValueError(f"Expect CONFIG: command or ENABLE: command, got {v}")
            mode = next(iter(v))
            command = v[mode]
        else:
            mode = ResourceCommandMode.ENABLE.value
            command = v
        return {"mode": mode, "command": command}


class DeploymentResourceConfig(BaseModel):
    name: str = Field(..., alias="Name")
    is_first_gen: bool = Field(False, alias="First Gen")
    attributes: dict[str, str] = Field({}, alias="Attributes")
    children_attributes: dict[str, dict[str, str]] = Field(
        {}, alias="Children Attributes"
    )
    blueprint_name: str = Field(..., alias="Blueprint Name")
    tests_conf: TestsConfig = Field(TestsConfig(), alias="Tests")


class AppConfig(BaseModel):
    name: str = Field(..., alias="Name")
    cp_resource_name: str = Field(..., alias="CP Resource Name")
    deployment: str = Field(..., alias="Deployment")
    attributes: dict[str, str] = Field({}, alias="Attributes")


class ServiceConfig(BaseModel):
    name: str = Field(..., alias="Name")
    shell_name: str = Field(None, alias="Shell Name")
    attributes: dict[str, str] = Field({}, alias="Attributes")
    tests_conf: TestsConfig = Field(TestsConfig(), alias="Tests")


class HostConfig(BaseModel):
    host: str = Field(..., alias="Host")

    @property
    def netloc(self) -> str:
        return self.host.split("/", 1)[0]

    @property
    def path(self) -> str:
        path = self.host.removeprefix(self.netloc)
        if path:
            path = f"/{path}"
        return path


class HostWithUserConfig(HostConfig):
    user: Optional[str] = Field(None, alias="User")
    password: Optional[str] = Field(None, alias="Password")


class ShellConfig(BaseModel):
    name: str = Field(..., alias="Name")
    path: Path = Field(..., alias="Path")
    dependencies_path: Optional[Path] = Field(None, alias="Dependencies Path")
    extra_standards_paths: list[Path] = Field([], alias="Extra CS Standards")
    tests_conf: TestsConfig = Field(TestsConfig(), alias="Tests")

    @validator(
        "path", "dependencies_path", "extra_standards_paths", pre=True, each_item=True
    )
    def _download_file(cls, path: str):
        return DownloadFile(path).path


class SandboxConfig(BaseModel):
    name: str = Field(..., alias="Name")
    resource_names: list[str] = Field([], alias="Resources")
    deployment_resource_names: list[str] = Field([], alias="Deployment Resources")
    service_names: list[str] = Field([], alias="Services")
    blueprint_name: Optional[str] = Field(None, alias="Blueprint Name")
    specific_version: Optional[str] = Field(None, alias="Specific Version")
    tests_conf: TestsConfig = Field(TestsConfig, alias="Tests")


class BlueprintConfig(BaseModel):
    name: str = Field(..., alias="Name")
    app_names: list[str] = Field([], alias="Apps")


class VcenterConfig(BaseModel):
    host: str = Field(..., alias="Host")
    user: str = Field(..., alias="User")
    password: str = Field(..., alias="Password")


class MainConfig(BaseModel):
    version: str = Field(..., alias="Version")
    do_conf: Optional[DoConfig] = Field(None, alias="Do")
    cs_conf: Optional[CloudShellConfig] = Field(None, alias="CloudShell")
    shells_conf: list[ShellConfig] = Field(..., alias="Shells")
    resources_conf: list[ResourceConfig] = Field(..., alias="Resources")
    deployment_resources_conf: list[DeploymentResourceConfig] = Field(
        [], alias="Deployment Resources"
    )
    apps_conf: list[AppConfig] = Field([], alias="Apps")
    services_conf: list[ServiceConfig] = Field([], alias="Services")
    ftp_conf: HostWithUserConfig = Field(..., alias="FTP")
    scp_conf: Optional[HostWithUserConfig] = Field(None, alias="SCP")
    tftp_conf: Optional[HostConfig] = Field(None, alias="TFTP")
    sandboxes_conf: list[SandboxConfig] = Field([], alias="Sandboxes")
    blueprints_conf: list[BlueprintConfig] = Field([], alias="Blueprints")
    vcenter_conf: Optional[VcenterConfig] = Field(None, alias="vCenter")

    @validator("version")
    def _is_compatible_version(cls, v: str):
        if str_version_to_tuple(v) < str_version_to_tuple(MIN_COMPATIBLE_CONF_VER):
            msg = f"Minimum compatible config version is {MIN_COMPATIBLE_CONF_VER}"
            raise ValueError(msg)
        elif str_version_to_tuple(v) > str_version_to_tuple(MAX_COMPATIBLE_CONF_VER):
            msg = (
                f"This version of Auto tests do not supported {v} version of config."
                f"Update Auto tests"
            )
            raise ValueError(msg)
        return v

    @validator("cs_conf", pre=True, always=True)
    def _check_cs_conf_or_do(cls, cs_conf, values: dict):
        cs_on_do_conf = getattr(values.get("do_conf"), "cs_on_do_conf", None)
        if not cs_on_do_conf and not cs_conf:
            raise ValueError("either CS on Do config or CloudShell config is required")
        return cs_conf

    @validator(
        "resources_conf", "services_conf", "deployment_resources_conf", each_item=True
    )
    def _merge_tests_config(cls, conf, values: dict):
        for shell_conf in values.get("shells_conf", []):
            if shell_conf.name == conf.shell_name:
                conf.tests_conf += shell_conf.tests_conf
                break
        return conf

    @classmethod
    def from_yaml(cls, file_path: Path) -> "MainConfig":
        with file_path.open() as f:
            data = yaml.safe_load(f)
        return cls.parse_obj(data)
