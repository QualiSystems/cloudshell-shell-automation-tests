from operator import itemgetter
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, root_validator, validator

from shell_tests.helpers.download_files_helper import DownloadFile


class CloudShellConfig(BaseModel):
    host: str = Field(..., alias="Host")
    user: str = Field(..., alias="User")
    password: str = Field(..., alias="Password")
    os_user: str = Field("", alias="OS User")
    os_password: str = Field("", alias="OS Password")
    domain: str = Field("Global", alias="Domain")


class DoConfig(CloudShellConfig):
    cs_version: str = Field("CloudShell 9.3 GA - IL", alias="CS Version")
    delete_cs: bool = Field(True, alias="Delete CS")
    cs_specific_version: str = Field("", alias="CS Specific Version")


class TestsConfig(BaseModel):
    expected_failures: Dict[str, str] = Field({}, alias="Expected failures")
    run_tests: bool = Field(True, alias="Run Tests")

    def __iadd__(self, other: "TestsConfig"):
        if not isinstance(other, TestsConfig):
            raise NotImplementedError("You can add only TestsConfig")
        self.expected_failures = {**other.expected_failures, **self.expected_failures}
        self.run_tests = other.run_tests
        return self


class ResourceConfig(BaseModel):
    name: str = Field(..., alias="Name")
    shell_name: str = Field(..., alias="Shell Name")
    device_ip: Optional[str] = Field(None, alias="Device IP")
    attributes: Dict[str, str] = Field({}, alias="Attributes")
    children_attributes: Dict[str, Dict[str, str]] = Field(
        {}, alias="Children Attributes"
    )
    tests_conf: TestsConfig = Field(TestsConfig(), alias="Tests")
    is_first_gen: bool = Field(False, alias="First Gen")


class DeploymentResourceConfig(BaseModel):
    name: str = Field(..., alias="Name")
    is_first_gen: bool = Field(False, alias="First Gen")
    attributes: Dict[str, str] = Field({}, alias="Attributes")
    children_attributes: Dict[str, Dict[str, str]] = Field(
        {}, alias="Children Attributes"
    )
    blueprint_name: str = Field(..., alias="Blueprint Name")
    tests_conf: TestsConfig = Field(TestsConfig(), alias="Tests")


class ServiceConfig(BaseModel):
    name: str = Field(..., alias="Name")
    shell_name: str = Field(None, alias="Shell Name")
    attributes: Dict[str, str] = Field({}, alias="Attributes")
    tests_conf: TestsConfig = Field(TestsConfig(), alias="Tests")


class FTPConfig(BaseModel):
    host: str = Field(..., alias="Host")
    user: Optional[str] = Field(None, alias="User")
    password: Optional[str] = Field(None, alias="Password")


class ShellConfig(BaseModel):
    name: str = Field(..., alias="Name")
    path: Path = Field(..., alias="Path")
    dependencies_path: Optional[Path] = Field(None, alias="Dependencies Path")
    extra_standards_paths: List[Path] = Field([], alias="Extra CS Standards")
    tests_conf: TestsConfig = Field(TestsConfig(), alias="Tests")

    @validator(
        "path", "dependencies_path", "extra_standards_paths", pre=True, each_item=True
    )
    def _download_file(cls, path: str):
        return DownloadFile(path).path  # todo download files when use it; descriptor?


class SandboxConfig(BaseModel):
    name: str = Field(..., alias="Name")
    resource_names: List[str] = Field(..., alias="Resources")
    deployment_resource_names: List[str] = Field([], alias="Deployment Resources")
    service_names: List[str] = Field([], alias="Services")
    blueprint_name: Optional[str] = Field(None, alias="Blueprint Name")
    specific_version: Optional[str] = Field(None, alias="Specific Version")
    tests_conf: TestsConfig = Field(TestsConfig, alias="Tests")

    @root_validator
    def _resource_or_service_included(cls, values):
        names = itemgetter(
            "resource_names", "deployment_resource_names", "services_names"
        )
        if not any(map(names, values)):
            raise ValueError(
                "You should provide Resources or Deployment Resources or Services"
            )
        return values


class BlueprintConfig(BaseModel):
    name: str = Field(..., alias="Name")
    path: Path = Field(..., alias="Path")

    @validator("path", pre=True)
    def _download_file(cls, path: str):
        return DownloadFile(path).path


class VcenterConfig(BaseModel):
    host: str = Field(..., alias="Host")
    user: str = Field(..., alias="User")
    password: str = Field(..., alias="Password")


class MainConfig(BaseModel):
    do_conf: Optional[DoConfig] = Field(None, alias="Do")
    cs_conf: Optional[CloudShellConfig] = Field(None, alias="CloudShell")
    shells_conf: List[ShellConfig] = Field(..., alias="Shells")
    resources_conf: List[ResourceConfig] = Field(..., alias="Resources")
    deployment_resources_conf: List[DeploymentResourceConfig] = Field(
        [], alias="Deployment Resources"
    )
    services_conf: List[ServiceConfig] = Field([], alias="Services")
    ftp_conf: FTPConfig = Field(..., alias="FTP")
    sandboxes_conf: List[SandboxConfig] = Field(..., alias="Sandboxes")
    blueprints_conf: List[BlueprintConfig] = Field([], alias="Blueprints")
    vcenter_conf: Optional[VcenterConfig] = Field(None, alias="vCenter")

    @validator("cs_conf", pre=True, always=True)
    def _check_cs_conf_or_do(cls, cs_conf, values: dict):
        if not values.get("do_conf") and not cs_conf:
            raise ValueError("either Do config or CloudShell config is required")
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
