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
import shlex
import subprocess
from exceptions import LogException, PackageException


def system_run(command, env_vars=None):
    if env_vars is None:
        env_vars = {}

    shell_env = os.environ.copy()
    env_vars = {key: os.path.expandvars(val) for key, val in env_vars.items()}
    shell_env.update(env_vars)

    try:
        logging.debug(
            f"Calling {shlex.split(command)}:"
        )
        subprocess.run(
            shlex.split(command), check=True, env=shell_env
        )
    except subprocess.CalledProcessError:
        raise PackageException(f"following command failed: {command}")


class Logging():
    log_priorities = {
        "debug": 4,
        "info": 3,
        "warning": 2,
        "error": 1
    }

    def __init__(self, level):
        try:
            self.log_priority = self.log_priorities[level.lower()]
        except KeyError:
            LogException("no log level '{level}'")

    def debug(self, msg):
        self._print_to_stdout(msg, level="debug")

    def info(self, msg):
        self._print_to_stdout(msg, level="info")

    def warning(self, msg):
        self._print_to_stdout(msg, level="warning")

    def error(self, msg):
        self._print_to_stdout(msg, level="error")

    def _print_to_stdout(self, msg, level):
        if self.log_priorities[level] <= self.log_priority:
            print(f"{level}: {msg}")


logging = Logging("info")
