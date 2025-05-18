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
import os

name = "elmer"
envmngr_path = os.path.join(os.path.dirname(__file__), "..", "..", "envmngr")
sys.path.append(envmngr_path)

env_root_path = os.path.join(os.environ['HOME'], f"opt/{name}-env")
env_bin_path = os.path.join(env_root_path, "bin/")
env_lib_path = os.path.join(env_root_path, "lib/")
env_include_path = os.path.join(env_root_path, "include/")

os.environ["PATH"] = f"{env_bin_path}:{os.environ['PATH']}"
try:
    os.environ["LD_LIBRARY_PATH"] = (
        f"{env_lib_path}: {os.environ['LD_LIBRARY_PATH']}"
    )
except KeyError:
    os.environ["LD_LIBRARY_PATH"] = f"{env_lib_path}"
try:
    os.environ["CPATH"] = f"{env_include_path}:{os.environ['CPATH']}"
except KeyError:
    os.environ["CPATH"] = f"{env_include_path}"
os.environ["CMAKE_PREFIX_PATH"] = env_root_path

# overrides manifest flags
FORCE_FLAGS = {
    "petsc": {
        "configFLAGS": [
            f"--with-blaslapack-dir={env_root_path}",
            f"--with-mpi-dir={env_root_path}",
            f"--with-zlib-dir={env_root_path}",
            f"--with-netcdf-dir={env_root_path}",
            f"--with-hdf5-dir={env_root_path}",
            f"--with-eigen-dir={env_root_path}",
            f"--with-scalapack-dir={env_root_path}",
            "--COPTFLAGS=-O2",
            "--CXXOPTFLAGS=-O2",
            "--FOPTFLAGS=-O2",
            "--download-mumps=1",
            "--download-suitesparse=1",
            "--download-metis=1",
            "--download-parmetis=1"
        ]
    }
}
