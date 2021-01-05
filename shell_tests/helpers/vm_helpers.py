import itertools
import zipfile
from collections import defaultdict

import xmltodict


def parse_connections(source_name, source_ports, target_name, target_ports):
    """Parse ports from blueprint.

    :param str source_name: blueprint resource name
    :param str source_ports: requested ports to connect, "2,3", "", ...
    :param str target_name: blueprint resource name
    :param str target_ports: requested ports to connect, "3,2", "", ...
    :rtype: dict[tuple[str, str], list[tuple[str, str]]]
    :return:
        {
            (first_resource, requested_port_name):
                [(second_resource, requested_port_name)]
        }
    """
    connections = defaultdict(list)

    target_ports = target_ports.split(",")
    source_ports = source_ports.split(",")

    for source_port, target_port in itertools.zip_longest(
        source_ports, target_ports, fillvalue="any"
    ):
        connections[(source_name, source_port)].append((target_name, target_port))

    return connections


def get_str_connections_form_blueprint(path, bp_name):
    """Get a list of connections in the blueprint.

    :param path: path to a package zip file
    :type path: str
    :param bp_name: name of the Blueprint
    :type bp_name: str
    :rtype: tuple[tuple[str, str], tuple[str, str]]
    :return: (first_resource_name, requested_port_names),
        (second_resource_name, requested_port_names)
    """
    xml_name = f"{bp_name}.xml"
    xml_path = f"Topologies/{xml_name}"

    with zipfile.ZipFile(path) as zip_file:
        xml_data = zip_file.read(xml_path)

    data = xmltodict.parse(xml_data)
    source_ports = target_ports = "any"

    connector = data["TopologyInfo"]["Routes"]["Connector"]
    source_name = connector["@Source"]
    target_name = connector["@Target"]

    for attribute in connector.get("Attributes", {}).get("Attribute", []):
        if attribute["@Name"] == "Requested Target vNIC Name":
            target_ports = attribute["@Value"]
        elif attribute["@Name"] == "Requested Source vNIC Name":
            source_ports = attribute["@Value"]

    return source_name, source_ports, target_name, target_ports
