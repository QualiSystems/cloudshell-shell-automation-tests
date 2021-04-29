from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

import xmltodict

from shell_tests.helpers.package_api.app_position import AppPositionOnBlueprint


def _create_attributes(
    attributes: dict[str, str], deployment_path=""
) -> dict[str, list[dict[str, str]]]:
    name_space = f"{deployment_path}." if deployment_path else ""
    return {
        "Attribute": [
            {"@Name": f"{name_space}{key}", "@Value": val}
            for key, val in attributes.items()
        ]
    }


def get_bool(v: bool) -> str:
    return str(v).lower()


class XmlNode(ABC):
    @abstractmethod
    def to_xml_dict(self) -> dict:
        raise NotImplementedError()


class XmlRoot(XmlNode):
    @abstractmethod
    def get_xml_root_dict(self) -> dict:
        raise NotImplementedError()

    def get_xml(self) -> str:
        return xmltodict.unparse(self.get_xml_root_dict(), short_empty_elements=True)


class MetaData(XmlRoot):
    def __init__(self, cs_version="9.3.0", now: Optional[datetime] = None):
        if not cs_version:
            cs_version = "9.3.0"
        self.cs_version = cs_version
        self.now = now

    def to_xml_dict(self) -> dict:
        now = self.now or datetime.now() - timedelta(days=1)
        now_str = now.strftime("%d/%m/%Y %H:%M:%S")
        return {
            "CreationDate": now_str,
            "ServerVersion": self.cs_version,
            "PackageType": "CloudShellPackage",
        }

    def get_xml_root_dict(self) -> dict:
        return {
            "Metadata": {
                "@xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
                "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "@xmlns": "http://schemas.qualisystems.com/PackageMetadataSchema.xsd",
                **self.to_xml_dict(),
            }
        }


class DeploymentPath(XmlNode):
    def __init__(
        self,
        cp_name: str,
        cp_model: str,
        deployment_path: str,
        attributes: dict[str, str],
    ):
        self.cp_name = cp_name
        self.cp_model = cp_model
        self.deployment_path = deployment_path
        self.attributes = attributes
        self.is_default = False

    def to_xml_dict(self) -> dict:
        if self.deployment_path.startswith(f"{self.cp_model}."):
            dp = self.deployment_path
        else:
            dp = f"{self.cp_model}.{self.deployment_path}"

        return {
            "@Name": f"{self.cp_name} - {dp}",
            "@Default": get_bool(self.is_default),
            "DeploymentService": {
                "@Name": dp,
                "@CloudProvider": self.cp_name,
                "Attributes": _create_attributes(self.attributes, dp),
            },
        }


class App(XmlRoot):
    def __init__(self, name: str, deployment_paths: list[DeploymentPath]):
        self.name = name
        self.deployment_paths = deployment_paths
        self.default_app_resource = {
            "@ModelName": "Generic App Model",
            "@Driver": "",
            "Attributes": _create_attributes(
                {"Password": "", "Public IP": "", "User": ""}
            ),
        }

    def to_xml_dict(self) -> dict:
        deployment_paths = [dp.to_xml_dict() for dp in self.deployment_paths]
        return {
            "AppResourceInfo": {
                "@Name": self.name,
                "AppResources": {"AppResource": [self.default_app_resource]},
                "DeploymentPaths": {"DeploymentPath": deployment_paths},
            },
        }

    def get_xml_root_dict(self) -> dict:
        return {
            "AppTemplateInfo": {
                "@xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
                "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                **self.to_xml_dict(),
                "Categories": {"Category": ["Applications"]},
            }
        }


class Blueprint(XmlRoot):
    def __init__(self, name: str, apps: list[App]):
        self.name = name
        self.apps = apps
        self.position_gen = AppPositionOnBlueprint()

    def _get_new_position(self):
        x, y = self.position_gen.get_new_position()
        return {"@PositionX": str(x), "@PositionY": str(y)}

    def get_apps_dict(self) -> list[dict]:
        for app in self.apps:
            # set first DP to be default
            app.deployment_paths[0].is_default = True

        return [
            {
                **self._get_new_position(),
                "@TemplateName": app.name,
                **app.to_xml_dict(),
            }
            for app in self.apps
        ]

    def to_xml_dict(self) -> dict:
        return {
            "Details": {
                "@Name": self.name,
                "@Public": "false",
                "@Driver": "Python Setup & Teardown",
                "@SetupDuration": "10",
                "@TeardownDuration": "10",
                "@EnableSandboxSave": "true",
                "Scripts": {
                    "Script": [
                        {"@Name": "Default Sandbox Save 3.0"},
                        {"@Name": "Default Sandbox Teardown 3.0"},
                        {"@Name": "Default Sandbox Restore 3.0"},
                        {"@Name": "Default Sandbox Setup 3.0"},
                    ]
                },
            }
        }

    def get_xml_root_dict(self) -> dict:
        return {
            "TopologyInfo": {
                "@xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
                "@xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                **self.to_xml_dict(),
                "Apps": {"App": self.get_apps_dict()},
            }
        }
