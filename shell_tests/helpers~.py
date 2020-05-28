def get_str_connections_form_blueprint(path, bp_name):
    """Get a list of connections in the blueprint.

    :param path: path to a package zip file
    :type path: str
    :param bp_name: name of the Blueprint
    :type bp_name: str
    :rtype: tuple[tuple[str, str], tuple[str, str]]
    :return: (first_resource_name, requested_port_names), (second_resource_name, requested_port_names)
    """
    xml_name = "{}.xml".format(bp_name)
    xml_path = "Topologies/{}".format(xml_name)

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


def parse_connections(source_name, source_ports, target_name, target_ports):
    """Parse ports from blueprint.

    :param str source_name: blueprint resource name
    :param str source_ports: requested ports to connect, "2,3", "", ...
    :param str target_name: blueprint resource name
    :param str target_ports: requested ports to connect, "3,2", "", ...
    :rtype: dict[tuple[str, str], list[tuple[str, str]]]
    :return:
        {
            (first_resource, requested_port_name): [(second_resource, requested_port_name)]
        }
    """
    connections = defaultdict(list)

    target_ports = target_ports.split(",")
    source_ports = source_ports.split(",")

    for source_port, target_port in itertools.izip_longest(
        source_ports, target_ports, fillvalue="any"
    ):
        connections[(source_name, source_port)].append((target_name, target_port))

    return connections


class patch_logging(object):
    """Change log level to DEBUG in cloudshell-core and cloudshell-logging.

    :type zip_ext_file: zipfile.ZipExtFile
    """

    FILE_PATTERN = re.compile(
        r"^(cloudshell[-_]core|cloudshell[-_]logging)-(\d+\.?)+"
        r"(-\w+(\.\w+)?-\w+-\w+)?"
        r"\.(tar\.gz|zip|whl)$"
    )

    def __init__(self, zip_ext_file):
        self._zip_ext_file = zip_ext_file
        self._tmp_dir = None
        self._archive_obj = None

    def _extract_archive(self, buffer_, ext):
        """Extract the archive to tmp dir and returns path to extracted dir.

        :type buffer_: BytesIO
        :type ext: str
        :rtype: str
        """
        if ext in ("zip", "whl"):
            arch_file = zipfile.ZipFile(buffer_)
        elif ext == "tar.gz":
            arch_file = tarfile.open(fileobj=buffer_)
        else:
            raise ValueError("Unsupported extension")

        if self._tmp_dir is None:
            self._tmp_dir = tempfile.mkdtemp()
        arch_file.extractall(self._tmp_dir)
        if ext == "whl":
            dir_path = self._tmp_dir
        else:
            dir_path = glob.glob("{}/**".format(self._tmp_dir))[0]
        return dir_path

    @staticmethod
    def _rewrite_config_file(package_dir, package_name):
        if package_name == "cloudshell-core":
            config_path = os.path.join(
                package_dir, "cloudshell/core/logger/qs_config.ini"
            )
        elif package_name == "cloudshell-logging":
            config_path = os.path.join(package_dir, "cloudshell/logging/qs_config.ini")
        else:
            raise ValueError("Unsupported package {}".format(package_name))

        with open(config_path) as f:
            config_str = f.read()

        config_str = config_str.replace("'INFO'", "'DEBUG'")
        config_str = config_str.replace('"INFO"', '"DEBUG"')

        with open(config_path, "w") as f:
            f.write(config_str)

    def _archive_folder_to_zip(self, dir_path, zip_path):
        with zipfile.ZipFile(zip_path, "w") as zip_file:
            for cur_dir, sub_dirs, files in os.walk(dir_path):
                for file_name in files:
                    file_path = os.path.join(cur_dir, file_name)
                    if zip_path == file_path:
                        continue

                    file_arch_path = os.path.relpath(file_path, self._tmp_dir)
                    zip_file.write(file_path, file_arch_path)

    def _save_new_archive(self, archive_name, archive_ext, package_path):
        archive_path = os.path.join(self._tmp_dir, archive_name)
        if archive_ext in ("zip", "whl"):
            self._archive_folder_to_zip(package_path, archive_path)
        elif archive_ext == "tar.gz":
            with tarfile.open(archive_path, "w:gz") as tar_file:
                tar_file.add(package_path, os.path.basename(package_path))
        else:
            raise ValueError("Unsupported archive type {}".format(archive_ext))
        return archive_path

    def _remove_tmp_files(self):
        if self._tmp_dir is not None:
            shutil.rmtree(self._tmp_dir)
        if self._archive_obj is not None:
            self._archive_obj.close()

    def __enter__(self):
        """:rtype: file"""
        try:
            match = self.FILE_PATTERN.match(self._zip_ext_file.name)
            if not match:
                return self._zip_ext_file

            ext = match.group(5)
            package_name = match.group(1).replace("_", "-")
            buffer_ = BytesIO(self._zip_ext_file.read())
            extracted_dir = self._extract_archive(buffer_, ext)
            self._rewrite_config_file(extracted_dir, package_name)
            archive_path = self._save_new_archive(
                self._zip_ext_file.name, ext, extracted_dir
            )
            self._archive_obj = open(archive_path, "rb")
        except Exception as e:
            self._remove_tmp_files()
            raise e

        return self._archive_obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._remove_tmp_files()
        return False
