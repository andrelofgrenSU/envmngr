"""
    This file is part of envmngr.

    envmngr is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    envmngr is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with envmngr.  If not, see <https://www.gnu.org/licenses/>.
"""
import os
import shutil
import threading
import functools
import time
import hashlib
import tarfile
import json
import requests
from utils import system_run, logging
from exceptions import PackageException


class DownloadProgress(threading.Thread):
    """
    Prints download progress while the main thread is downloading
    """

    def __init__(self, pkg_JSON, file_size=None):
        super().__init__()
        self.file_size = file_size
        self.bytes_received = 0
        self.bytes_received_previously = 0
        self.update_interval_ms = 500
        self.is_downloading = True
        self.pkg_JSON = pkg_JSON

    @property
    def progress(self):
        return round(100*self.bytes_received/self.file_size, 1)

    def progress_bar_str(self):
        progress_str = "["
        if self.file_size is not None:
            nof_bar_cols = os.get_terminal_size().columns // 4
            for col_index in range(nof_bar_cols):
                if self.progress > 100/nof_bar_cols*col_index:
                    progress_str += "="
                else:
                    progress_str += " "
            progress_str = progress_str[::-1].replace("=", ">", 1)[::-1]
        else:
            progress_str += "n/a"
        progress_str += "]"
        return progress_str

    def progress_info_str(self):
        dl_speed_MB = (
            (self.bytes_received - self.bytes_received_previously)*1e-6
            /(self.update_interval_ms * 1e-3)
        )
        file_received_MB = self.bytes_received*1e-6

        progress_str = " "
        if self.file_size is not None:
            file_size_MB = self.file_size*1e-6
        else:
            try:
                file_size_MB = self.pkg_JSON["fileSize"]
            except KeyError:
                file_size_MB = 0.0

        if file_size_MB != 0.0:
            try:
                dl_seconds_left = int(
                    (file_size_MB - file_received_MB)/dl_speed_MB
                )
            except ZeroDivisionError:
                dl_seconds_left = 0
        else:
            dl_seconds_left = 0

        time_left_str = self.seconds_to_dhms(dl_seconds_left)
        return self.info_str_fmt(
            file_received_MB, file_size_MB, dl_speed_MB, time_left_str
        )

    @staticmethod
    def info_str_fmt(file_received, file_size, dl_speed, time_str):
        return (
            f" {file_received:.2f}/{file_size:.2f} MB,"
            + f" {dl_speed:.2f} MB/s, {time_str}"
        )

    @staticmethod
    def seconds_to_dhms(seconds):
        dhms_str = ""

        days = seconds // 86400
        seconds %= 86400
        dhms_str += f"{days} d " if days else ""

        hours = seconds // 3600
        seconds %= 3600
        dhms_str += f"{hours} h " if hours else ""

        minutes = seconds // 60
        seconds %= 60
        dhms_str += f"{minutes} m " if minutes else ""
        dhms_str += f"{seconds} s "
        return dhms_str

    def run(self):
        start_time = time.time()
        while self.is_downloading:
            self.clear_line()
            progress_str = f"{self.pkg_JSON['pkgName']} "
            progress_str += self.progress_bar_str()
            progress_str += self.progress_info_str()
            print(progress_str, end="\r")
            self.bytes_received_previously = self.bytes_received
            time.sleep(self.update_interval_ms*1e-3)
        self.clear_line()
        progress_str = f"{self.pkg_JSON['pkgName']} "
        progress_str += self.progress_bar_str()

        dl_time = time.time() - start_time
        time_elapsed_str = self.seconds_to_dhms(int(dl_time))
        file_size_MB = self.bytes_received*1e-6
        avg_dl_speed = file_size_MB/dl_time
        progress_str += self.info_str_fmt(
            file_size_MB, file_size_MB, avg_dl_speed, time_elapsed_str
        )

        print(progress_str, end="\n")

    def clear_line(self):
        print(os.get_terminal_size().columns * " ", end="\r")


class PackageInstaller:
    """Class handling the installation of a single package"""

    def __init__(self, pkg_name, pkg_JSON, env_path):
        self.pkg_name = pkg_name
        self.pkg_JSON = pkg_JSON
        self.env_path = env_path

        self.download_path = os.path.join(self.env_path, "tmp")
        self.tarball_path = os.path.join(
            self.download_path,  f"{self.pkg_name}.tar.gz"
        )
        self.extract_path = os.path.join(self.env_path, "src")

    @property
    def source_path(self):
        with tarfile.open(self.tarball_path) as tar_file:
            file_path_split = os.path.split(tar_file.getnames()[0])
            if file_path_split[0] != "":
                extracted_file = file_path_split[0]
            else:
                extracted_file = file_path_split[1]
        path = os.path.join(self.extract_path, extracted_file)
        if "sourceDir" in self.pkg_JSON:
            path = os.path.join(path, self.pkg_JSON["sourceDir"])
        return path

    @property
    def build_path(self):
        if "createBuildDir" in self.pkg_JSON and self.pkg_JSON["createBuildDir"]:
            return os.path.join(
                self.source_path,
                "build"
            )
        else:
            return self.source_path

    def download(self, block_size=65536, get_size_retries=10):
        pkg_url = self.pkg_JSON["srcURL"]

        file_size = None
        for retry in range(get_size_retries):
            response = requests.get(pkg_url, stream=True)
            try:
                file_size = int(response.headers["content-length"])
                break
            except KeyError:
                time.sleep(0.05)
                continue

        response.raise_for_status()
        download_progress = DownloadProgress(self.pkg_JSON, file_size)

        download_progress.start()

        tar_file_name = os.path.join(
            self.download_path, f"{self.pkg_name}.tar.gz"
        )
        os.makedirs(self.download_path, exist_ok=True)

        bytes_read = 0
        # Download data chunks
        with open(tar_file_name, "wb") as tar_file:
            for data_chunk in response.iter_content(chunk_size=block_size):
                if data_chunk:
                    tar_file.write(data_chunk)
                    download_progress.bytes_received += len(data_chunk)

        download_progress.is_downloading = False
        download_progress.join()

    def verify(self, block_size=65536):
        pkg_hash = hashlib.sha256()

        with open(self.tarball_path, "rb") as tar_file:
            while True:
                data_chunk = tar_file.read()
                pkg_hash.update(data_chunk)
                if not data_chunk:
                    break
        if pkg_hash.hexdigest() != self.pkg_JSON["sha256"]:
            raise PackageException(
                f"{self.pkg_name} "
                "failed integrity check"
            )

    def extract(self):
        with tarfile.open(self.tarball_path) as tar_file:
            tar_file.extractall(self.extract_path)

    def configure(self):
        try:
            ENVARS = self.pkg_JSON["ENVARS"]
        except KeyError:
            ENVARS = {}

        try:
            config_flags = self.pkg_JSON["configFLAGS"]
        except KeyError:
            config_flags = []

        logging.debug(
            f"{self.pkg_name}: configuring with environment variables: {ENVARS}"
        )

        if not os.path.exists(self.build_path):
            os.makedirs(self.build_path)
        os.chdir(self.build_path)

        try:
            system_run(
                f"{self.pkg_JSON['configCommand']} {self.pkg_JSON['prefixCommand']}{os.path.join(self.env_path, self.pkg_JSON['prefix'])} {' '.join(config_flags)}",
                ENVARS
            )
        except KeyError:
            if "configCommand" not in self.pkg_JSON:
                error_msg = f"{self.pkg_name}: missing configCommand"
            elif "prefix" not in self.pkg_JSON:
                error_msg = f"{self.pkg_name}: missing configCommand"
            else:
                error_msg = f"{self.pkg_name}: missing prefixCommand"
            raise PackageException(error_msg)

    def compile(self):
        try:
            ENVARS = self.pkg_JSON["ENVARS"]
        except KeyError:
            ENVARS = {}

        try:
            make_flags = self.pkg_JSON["makeFLAGS"]
        except KeyError:
            make_flags = []

        os.chdir(self.build_path)

        try:
            system_run(
                f"{self.pkg_JSON['buildCommand']} {' '.join(make_flags)}",
                ENVARS
            )
        except KeyError:
            raise PackageException(
                f"{self.pkg_name}: missing buildCommand"
            )

    def test(self):
        os.chdir(self.build_path)
        try:
            system_run(f"{self.pkg_JSON['testCommand']}")
        except KeyError:
            raise PackageException(
                f"{self.pkg_JSON['pkgName']}: missing testCommand"
            )

    def install(self):
        os.chdir(self.build_path)
        try:
            system_run(f"{self.pkg_JSON['installCommand']}")
        except KeyError:
            raise PackageException(
                f"{self.pkg_JSON['pkgName']}: missing installCommand"
            )


def check_prerequisites(operation):

    def decorator(pkg_method):
        @functools.wraps(pkg_method)
        def wrapped_method_call(self, pkg_name):

            def check_dependencies(manifest, pkg_name):
                logging.debug(f"{pkg_name}: checking dependencies")
                missing_deps = []
                check_failed = False
                for dep in manifest[pkg_name]["dependencies"]:
                    logging.debug(f"{4*' '} {dep}")
                    if not manifest[dep]["installed"]:
                        check_failed = True
                        missing_deps.append(dep)
                if check_failed:
                    missing_deps_str = "'"
                    missing_deps_str += "' '".join(missing_deps)
                    missing_deps_str += "'"
                    raise PackageException(
                        f"{pkg_name}: dependencies {missing_deps_str} are "
                        " not flagged as installed"
                    )
                else:
                    logging.debug(f"{pkg_name}: dependency check passed")

            logging.debug(
                f"{pkg_name}: checking prerequisites for {operation}"
            )
            with open(self.manifest_path, "r") as manifest_JSON:
                manifest = json.load(manifest_JSON)
            pkg_JSON = manifest[pkg_name]

            if operation == "download":
                operation_flag = "downloaded"
            elif operation == "verify":
                operation_flag = "verified"
                if not pkg_JSON["downloaded"]:
                    raise PackageException(
                        f"{pkg_name}: integrity check could not be performed: "
                        "package not flagged as downloaded"
                    )
            elif operation == "extract":
                operation_flag = "extracted"
                if not pkg_JSON["verified"]:
                    raise PackageException(
                        f"{pkg_name}: extraction could not be performed: "
                        "package integrity not flagged as verified"
                    )
            elif operation == "configure":
                operation_flag = "configured"
                if not pkg_JSON["extracted"]:
                    raise PackageException(
                        f"{pkg_name}: configuration could not be performed: "
                        "package not flagged as extracted"
                    )
                check_dependencies(manifest, pkg_name)
            elif operation == "compile":
                operation_flag = "compiled"
                if not pkg_JSON["configured"]:
                    raise PackageException(
                        f"{pkg_name}: compilation could not be performed: "
                        "package not flagged as configured"
                    )
            elif operation == "test":
                operation_flag = "tested"
                if not pkg_JSON["compiled"]:
                    raise PackageException(
                        f"{pkg_name}: testing could not be performed: "
                        "package not flagged as compiled"
                    )
                check_dependencies(manifest, pkg_name)
            elif operation == "install":
                operation_flag = "installed"
                if not pkg_JSON["tested"]:
                    raise PackageException(
                        f"{pkg_name}: installation could not be performed:"
                        "package not flagged as tested"
                    )
                check_dependencies(manifest, pkg_name)
            else:
                raise PackageException(
                    f"unknown operation '{operation}'"
                )

            if not pkg_JSON[operation_flag]:
                logging.debug(f"{pkg_name}: performing operation {operation}")
                pkg_method(self, pkg_name, pkg_JSON)
                logging.debug(f"{pkg_name}: {operation} succeded")
                with open(self.manifest_path, "w") as manifest_JSON:
                    logging.debug(
                        f"{pkg_name}: writing to {self.manifest_path}"
                    )
                    manifest[pkg_name][operation_flag] = True
                    logging.debug(json.dumps(manifest, indent=4))
                    json.dump(manifest, manifest_JSON, indent=4)
                logging.debug(f"{pkg_name}: flag {operation_flag} set to true")
            else:
                logging.debug(
                    f"{pkg_name}: {operation} flagged true; skipping"
                )

        return wrapped_method_call
    return decorator


class PackageManager():
    """Class handling all packages in the environment"""

    def __init__(self, env_path, manifest_path):
        self.env_path = env_path
        self.manifest_path = os.path.abspath(manifest_path)
        self.packages = self._packages

    @property
    def _packages(self):
        with open(self.manifest_path, "r") as manifest_JSON:
            return tuple(json.load(manifest_JSON).keys())

    @check_prerequisites("download")
    def download_pkg(self, pkg_name, pkg_JSON):
        PackageInstaller(pkg_name, pkg_JSON, self.env_path).download()

    @check_prerequisites("verify")
    def verify_pkg(self, pkg_name, pkg_JSON):
        PackageInstaller(pkg_name, pkg_JSON, self.env_path).verify()

    @check_prerequisites("extract")
    def extract_pkg(self, pkg_name, pkg_JSON):
        PackageInstaller(pkg_name, pkg_JSON, self.env_path).extract()

    @check_prerequisites("configure")
    def configure_pkg(self, pkg_name, pkg_JSON):
        PackageInstaller(pkg_name, pkg_JSON, self.env_path).configure()

    @check_prerequisites("compile")
    def compile_pkg(self, pkg_name, pkg_JSON):
        PackageInstaller(pkg_name, pkg_JSON, self.env_path).compile()

    @check_prerequisites("test")
    def test_pkg(self, pkg_name, pkg_JSON):
        PackageInstaller(pkg_name, pkg_JSON, self.env_path).test()

    @check_prerequisites("install")
    def install_pkg(self, pkg_name, pkg_JSON):
        PackageInstaller(pkg_name, pkg_JSON, self.env_path).install()

    def download(self):
        for pkg_name in self.packages:
            self.download_pkg(pkg_name)
        logging.info("finished downloading")

    def verify(self):
        for pkg_name in self.packages:
            self.verify_pkg(pkg_name)
        logging.info("integrity checks passed")

    def extract(self):
        for pkg_name in self.packages:
            self.extract_pkg(pkg_name)
        logging.info("packages extracted")

    def install(self):
        self.download()
        self.verify()
        self.extract()
        for pkg_name in self.packages:
            self.configure_pkg(pkg_name)
            logging.info(f"{pkg_name}: configuring done")
            self.compile_pkg(pkg_name)
            logging.info(f"{pkg_name}: compiling done")
            self.install_pkg(pkg_name)
            logging.info(f"{pkg_name}: installing done")

    def reset_pkg(self, pkg_name):
        def set_default_flags(manifest, pkg_name):
            manifest[pkg_name]["downloaded"] = False
            manifest[pkg_name]["verified"] = False
            manifest[pkg_name]["extracted"] = False
            manifest[pkg_name]["configured"] = False
            manifest[pkg_name]["compiled"] = False
            manifest[pkg_name]["tested"] = True
            manifest[pkg_name]["installed"] = False
            logging.info(f"{pkg_name}: reset package flags")

        with open(self.manifest_path, "r") as manifest_JSON:
            manifest = json.load(manifest_JSON)
        set_default_flags(manifest, pkg_name)
        with open(self.manifest_path, "w") as manifest_JSON:
            json.dump(manifest, manifest_JSON, indent=4)

    def reset(self):
        for pkg_name in self.packages:
            self.reset_pkg(pkg_name)
