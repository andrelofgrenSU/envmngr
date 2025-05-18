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
import sys
import argparse
import json
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
            logging.warning(f"Unable to find package {pkg_name} in manifest")
    with open(manifest_path, "w") as manifest_JSON:
        json.dump(manifest, manifest_JSON, indent=4)


def main():
    arg_parser = argparse.ArgumentParser(
        description="Install environment"
    )
    arg_parser.add_argument(
        "--manifest", help="Manifest path", type=str, required=True
    )
    arg_parser.add_argument(
        "--reset", help="Reset environments", action="store_true"
    )
    cmd_args = arg_parser.parse_args()
    manifest_path = cmd_args.manifest
    reset_env = cmd_args.reset

    pkg_mngr = PackageManager(environment.env_root_path, manifest_path)
    if reset_env:
        pkg_mngr.reset()
        sys.exit(0)

    preprocess_manifest(manifest_path)
    pkg_mngr.install()


if __name__ == "__main__":
    main()
