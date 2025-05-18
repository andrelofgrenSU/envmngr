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
import sys
import argparse
import environment as env
from package_manager import PackageManager
from utils import system_run


def main():
    arg_parser = argparse.ArgumentParser(
        description="Install environment"
    )
    arg_parser.add_argument(
        "--reset", help="Reset environments", action="store_true"
    )
    cmd_args = arg_parser.parse_args()
    if cmd_args.reset:
        system_run("python install_manifest.py --manifest manifest_python.json --reset")
        system_run("python install_manifest.py --manifest manifest_boost.json --reset")
        sys.exit(0)

    system_run("python install_manifest.py --manifest manifest_python.json")
    pip_exec = os.path.join(f"{env.env_bin_path}", "pip3")
    python_exec = os.path.join(f"{env.env_bin_path}", "python3")
    system_run(f"{pip_exec} install --upgrade pip")
    # system_run(f"{pip_exec} install numpy==1.26.4")
    # system_run(f"{pip_exec} install scipy==1.12.0")
    # system_run(f"{pip_exec} install matplotlib==3.9.4")
    # system_run(f"{pip_exec} install requests")
    # system_run(f"{python_exec} install_manifest.py --manifest manifest_boost.json")


if __name__ == "__main__":
    main()
