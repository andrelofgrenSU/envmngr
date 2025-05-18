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

name = "biceps"

envmngr_path = os.path.join(os.path.dirname(__file__), "..", "..", "envmngr")
sys.path.append(envmngr_path)

env_root_path = os.path.join(os.environ['HOME'], f"opt/{name}-env")
env_include_path = os.path.join(env_root_path, "include/")
env_lib_path = os.path.join(env_root_path, "lib/")
env_bin_path = os.path.join(env_root_path, "bin/")
py_include_path = os.path.join(env_include_path, "python3.10")
py_lib_path = os.path.join(env_lib_path, "libpython3.10.so")
py_exec_path = os.path.join(env_bin_path, "python3.10")

os.environ["PATH"] = f"{env_bin_path}:{os.environ['PATH']}"
try:
    os.environ["LD_LIBRARY_PATH"] = (
        f"{env_lib_path}:{os.environ['LD_LIBRARY_PATH']}"
    )
except KeyError:
    os.environ["LD_LIBRARY_PATH"] = f"{env_lib_path}"
try:
    os.environ["CPATH"] = f"{env_include_path}:{os.environ['CPATH']}"
except KeyError:
    os.environ["CPATH"] = f"{env_include_path}"
os.environ["CPATH"] = f"{py_include_path}:{os.environ['CPATH']}"
os.environ["CMAKE_PREFIX_PATH"] = env_root_path

# overrides manifest flags
FORCE_FLAGS = {
    "boost": {
        "ENVARS": {
            "CC": "cc",
            "CXX": "c++",
            "CXXFLAGS": "-fPIC -std=c++11"
        },
        "configFLAGS": [
            "--with-libraries=all",
            f"--with-python={os.path.join(env_bin_path, 'python3.10')}"
        ],
        "makeFLAGS": [
            "optimization=speed",
            "link=shared",
            "variant=release",
            "-j8"
        ]
    },
    "python": {
        "ENVARS": {
            "CC": "cc",
            "CXX": "c++",
            "CXXFLAGS": "-O3 -march=native -fPIC -std=c++11",
            "CFLAGS": "-O3 -march=native -fPIC",
            "LDFLAGS": f"-Wl,-rpath={env_lib_path}"
        },
        "configFLAGS": [
            "--enable-optimizations",
            "--with-lto",
            "--enable-shared",
            "--with-computed-gotos",
            f"--with-openssl={env_root_path}/openssl",
            f"--with-openssl-rpath={env_root_path}/openssl/lib",
            "--with-ensurepip=install"
        ],
        "makeFLAGS": [
            "-j8"
        ]
    },
    "eigenpy": {
        "ENVARS": {
            "CC": "cc",
            "CXX": "c++",
            "CXXFLAGS": "-std=c++11"
        },
        "configFLAGS": [
            "-DCMAKE_BUILD_TYPE=Release",
            "-DBUILD_SHARED_LIBS=ON",
            f"-DPYTHON_EXECUTABLE={py_exec_path}",
            f"-DPYTHON_LIBRARY={py_lib_path}"
        ],
        "makeFLAGS": [
            "-j8"
        ],
    }
}
