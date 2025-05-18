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
import json
import sys
import environment
from package_manager import PackageManager
from utils import logging


def preprocess_manifest(manifest_path):
    with open(manifest_path, "r") as manifest_JSON:
        manifest = json.load(manifest_JSON)
    for pkg_name in environment.FORCE_FLAGS:
        if pkg_name in manifest:
            pkg_dict = environment.FORCE_FLAGS[pkg_name]
            for k, v in pkg_dict.items():
                manifest[pkg_name].update({k: v})
        else:
            logging.warning("Unable to find package {pkg_name} in manifest")
    with open(manifest_path, "w") as manifest_JSON:
        json.dump(manifest, manifest_JSON, indent=4)


def main():
    preprocess_manifest("manifest.json")
    pkg_mngr = PackageManager(
        environment.env_root_path, "manifest.json"
    )

    if len(sys.argv) > 1:
        if sys.argv[1] == "--reset":
            pkg_mngr.reset()
        else:
            print(f"pkgmngr: unknown flag '{sys.argv[1]}'")
            sys.exit(-1)
    else:
        pkg_mngr.install()


if __name__ == "__main__":
    main()
