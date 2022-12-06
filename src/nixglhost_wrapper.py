#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import stat
import sys
import time
from glob import glob
from typing import List, Literal, Dict, Tuple, TypedDict, TextIO, Optional

IN_NIX_STORE = False


if IN_NIX_STORE:
    # The following paths are meant to be substituted by Nix at build
    # time.
    PATCHELF_PATH = "@patchelf-bin@"
else:
    PATCHELF_PATH = "patchelf"


class ResolvedLib:
    def __init__(self, name: str, fullpath: str, sha256: Optional[str] = None):
        self.name: str = name
        self.fullpath: str = fullpath
        if sha256 is None:
            h = hashlib.sha256()
            with open(fullpath, "rb") as f:
                h.update(f.read())
            sha: str = h.hexdigest()
        else:
            sha = sha256
        self.sha256: str = sha

    def __repr__(self):
        return f"ResolvedLib<{self.name}, {self.fullpath}, {self.sha256}>"

    def to_dict(self) -> Dict:
        return {"name": self.name, "fullpath": self.fullpath, "sha256": self.sha256}

    def __eq__(self, o):
        return (
            self.name == o.name
            and self.fullpath == o.fullpath
            and self.sha256 == o.sha256
        )

    @classmethod
    def from_dict(cls, d: Dict):
        return ResolvedLib(d["name"], d["fullpath"], d["sha256"])


class HostDSOs:
    def __init__(
        self,
        glx: Dict[str, ResolvedLib],
        cuda: Dict[str, ResolvedLib],
        generic: Dict[str, ResolvedLib],
        version: int = 1,
    ):
        self.glx = glx
        self.cuda = cuda
        self.generic = generic
        self.version = version

    def __eq__(self, other):
        return (
            self.glx == other.glx
            and self.cuda == other.cuda
            and self.generic == other.generic
            and self.version == other.version
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": 1,
                "glx": {k: v.to_dict() for k, v in self.glx.items()},
                "cuda": {k: v.to_dict() for k, v in self.cuda.items()},
                "generic": {k: v.to_dict() for k, v in self.generic.items()},
            },
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, o: str):
        d: Dict = json.loads(o)
        return HostDSOs(
            version=d["version"],
            glx={k: ResolvedLib.from_dict(v) for k, v in d["glx"].items()},
            cuda={k: ResolvedLib.from_dict(v) for k, v in d["cuda"].items()},
            generic={k: ResolvedLib.from_dict(v) for k, v in d["generic"].items()},
        )


# The following regexes list has been figured out by looking at the
# output of nix-build -A linuxPackages.nvidia_x11 before running
# ls ./result/lib | grep -E ".so$".
#
# TODO: find a more systematic way to figure out these names *not
# requiring to build/fetch the nvidia driver at runtime*.
NVIDIA_DSO_PATTERNS = [
    "libEGL_nvidia\.so.*$",
    "libGLESv1_CM_nvidia\.so.*$",
    "libGLESv2_nvidia\.so.*$",
    "libglxserver_nvidia\.so.*$",
    "libnvcuvid\.so.*$",
    "libnvidia-allocator\.so.*$",
    "libnvidia-cfg\.so.*$",
    "libnvidia-compiler\.so.*$",
    "libnvidia-eglcore\.so.*$",
    "libnvidia-egl-gbm\.so.*$",
    "libnvidia-egl-wayland\.so.*$",
    "libnvidia-encode\.so.*$",
    "libnvidia-fbc\.so.*$",
    "libnvidia-glcore\.so.*$",
    "libnvidia-glsi\.so.*$",
    "libnvidia-glvkspirv\.so.*$",
    "libnvidia-ml\.so.*$",
    "libnvidia-ngx\.so.*$",
    "libnvidia-nvvm\.so.*$",
    "libnvidia-opencl\.so.*$",
    "libnvidia-opticalflow\.so.*$",
    "libnvidia-ptxjitcompiler\.so.*$",
    "libnvidia-rtcore\.so.*$",
    "libnvidia-tls\.so.*$",
    "libnvidia-vulkan-producer\.so.*$",
    "libnvidia-wayland-client\.so.*$",
    "libnvoptix\.so.*$",
    # Host dependencies required by the nvidia DSOs to properly
    # operate
    # libdrm
    "libdrm\.so.*$",
    # libffi
    "libffi\.so.*$",
    # libgbm
    "libgbm\.so.*$",
    # Cannot find that one :(
    "libnvtegrahv\.so.*$",
    # libexpat
    "libexpat\.so.*$",
    # libxcb
    "libxcb-glx\.so.*$",
    # Coming from libx11
    "libX11-xcb\.so.*$",
    "libX11\.so.*$",
    "libXext\.so.*$",
    # libwayland
    "libwayland-server\.so.*$",
    "libwayland-client\.so.*$",
]

CUDA_DSO_PATTERNS = ["libcudadebugger\.so.*$", "libcuda\.so.*$"]

GLX_DSO_PATTERNS = ["libGLX_nvidia\.so.*$"]


def get_ld_paths() -> List[str]:
    """
    Vendored from https://github.com/albertz/system-tools/blob/master/bin/find-lib-in-path.py

    Find all the directories pointed by LD_LIBRARY_PATH and the ld cache."""

    def parse_ld_conf_file(fn: str) -> List[str]:
        paths = []
        for l in open(fn).read().splitlines():
            l = l.strip()
            if not l:
                continue
            if l.startswith("#"):
                continue
            if l.startswith("include "):
                dirglob = l[len("include ") :]
                if dirglob[0] != "/":
                    dirglob = os.path.dirname(os.path.normpath(fn)) + "/" + dirglob
                for sub_fn in glob(dirglob):
                    paths.extend(parse_ld_conf_file(sub_fn))
                continue
            paths.append(l)
        return paths

    LDPATH = os.getenv("LD_LIBRARY_PATH")
    PREFIX = os.getenv("PREFIX")  # Termux & etc.
    paths = []
    if LDPATH:
        paths.extend(LDPATH.split(":"))
    if os.path.exists("/etc/ld.so.conf"):
        paths.extend(parse_ld_conf_file("/etc/ld.so.conf"))
    else:
        print('WARNING: file "/etc/ld.so.conf" not found.')
    if PREFIX:
        if os.path.exists(PREFIX + "/etc/ld.so.conf"):
            paths.extend(parse_ld_conf_file(PREFIX + "/etc/ld.so.conf"))
        else:
            print('WARNING: file "' + PREFIX + '/etc/ld.so.conf" not found.')
        paths.extend(
            [
                PREFIX + "/lib",
                PREFIX + "/usr/lib",
                PREFIX + "/lib64",
                PREFIX + "/usr/lib64",
            ]
        )
    paths.extend(["/lib", "/usr/lib", "/lib64", "/usr/lib64"])
    return [path for path in paths if os.path.isdir(path)]


def resolve_libraries(
    paths: List[str], files_patterns: List[str]
) -> Dict[str, ResolvedLib]:
    """Scans the PATH directory looking for the files complying with
    the FILES_PATTERNS regexes list. Each file matching the pattern will be found only once

    Returns the list of the resolved DSOs."""
    libraries: Dict[str, ResolvedLib] = {}

    def is_dso_matching_pattern(filename):
        for pattern in files_patterns:
            if re.search(pattern, filename):
                return True
        return False

    for path in paths:
        for fname in os.listdir(path):
            abs_file_path = os.path.abspath(os.path.join(path, fname))
            if (
                os.path.isfile(abs_file_path)
                and is_dso_matching_pattern(abs_file_path)
                and (fname not in libraries)
            ):
                libraries[fname] = ResolvedLib(fname, abs_file_path)
    return libraries


def copy_and_patch_libs(dsos: List[ResolvedLib], libs_dir: str, rpath=None) -> None:
    """Copies the graphic vendor DSOs to the cache directory before
    patchelf-ing them.

    The DSOs can dlopen each other. Sadly, we don't want any host
    libraries to the LD_LIBRARY_PATH to prevent polluting the nix
    binary env. The only option left is to patch their ELFs runpath to
    point to RPATH.

    We also don't want to directly modify the host DSOs, we first copy
    them to the user's personal cache directory. We then alter their
    runpath to point to the cache directory."""
    rpath = rpath if (rpath is not None) else libs_dir
    for dso in dsos:
        basename = os.path.basename(dso.fullpath)
        newpath = os.path.join(libs_dir, basename)
        log_info(f"Copying and patching {dso} to {newpath}")
        shutil.copyfile(dso.fullpath, newpath)
        # Provide write permissions to ensure we can patch this binary.
        os.chmod(newpath, os.stat(dso.fullpath).st_mode | stat.S_IWUSR)
        patch_dso(newpath, rpath)


def log_info(string: str) -> None:
    """Prints STR to STDERR if the DEBUG environment variable is
    set."""
    if "DEBUG" in os.environ:
        print(f"[+] {string}", file=sys.stderr)


def patch_dso(dsoPath: str, rpath: str) -> None:
    """Call patchelf to change the DSOPATH runpath with RPATH."""
    log_info(f"Patching {dsoPath}")
    log_info(f"Exec: {PATCHELF_PATH} --set-rpath {rpath} {dsoPath}")
    res = subprocess.run([PATCHELF_PATH, "--set-rpath", rpath, dsoPath])
    if res.returncode != 0:
        raise BaseException(
            f"Cannot patch {dsoPath}. Patchelf exited with {res.returncode}"
        )

    # NOTE: is this the right abstraction? Looks like I'm stitching
    # some loosely connected parts together for no good reason.


def generate_nvidia_egl_config_files(
    cache_dir: str, libs_dir: str, egl_conf_dir: str
) -> str:
    """Generates a set of JSON files describing the EGL exec
    envirnoment to libglvnd.

    These configuration files will point to the EGL, wayland and GBM
    Nvidia DSOs."""

    def generate_egl_conf_json(dso):
        return json.dumps(
            {"file_format_version": "1.0.0", "ICD": {"library_path": dso}}
        )

    dso_paths = [
        ("10_nvidia.json", f"{libs_dir}/libEGL_nvidia.so.0"),
        ("10_nvidia_wayland.json", f"{libs_dir}/libnvidia-egl-wayland.so.1"),
        ("15_nvidia_gbm.json", f"{libs_dir}/libnvidia-egl-gbm.so.1"),
    ]

    for (conf_file_name, dso_path) in dso_paths:
        with open(
            os.path.join(egl_conf_dir, conf_file_name), "w", encoding="utf-8"
        ) as f:
            log_info(f"Writing {dso_path} conf to {egl_conf_dir}")
            f.write(generate_egl_conf_json(dso_path))

    return egl_conf_dir


def is_dso_cache_up_to_date(dsos: HostDSOs, cache_file_path: str) -> bool:
    """Check whether or not we need to udate the host DSOs cache.

    We keep what's in the cache through a JSON file stored at the root
    of the cache_dir. We consider a DSO to be up to date if its name
    and its content sha256 are equivalent.
    """
    log_info("Checking if the cache is up to date")
    if os.path.isfile(cache_file_path):
        with open(cache_file_path, "r", encoding="utf8") as f:
            try:
                cached_dsos: HostDSOs = HostDSOs.from_json(f.read())
            except:
                return False
            return dsos == cached_dsos
    return False


def nvidia_main(cache_dir: str, dso_vendor_paths: List[str]) -> Dict:
    """Prepares the environment necessary to run a opengl/cuda program
    on a Nvidia graphics card. It is by definition really stateful.

    Roughly, we're going to:

    1. Setup the nvidia cache directory.
    2. Find the nvidia DSOs in the DSO_VENDOR_PATH.
    3. Copy these DSOs to their appropriate cache directories.
    4. Generate the EGL configuration files.
    5. Patchelf the runpath of what needs to be patched.
    6. Generate the env variables the main process is supposed to set.

    Overall, we're using two different tricks to setup the GL/cuda envs:

    - For Cuda and GLX: we're isolating the main DSOs in their own
      dirs, add these dirs to the LD_LIBRARY_PATH and patch their
      runpath to point to the generic cache dir.
    - For EGL: we're generating some JSON configuration files.
      libglvnd will later use these configuration files to directly
      load the appropriate DSOs. We don't need any
      LD_LIBRARY_PATH-fueled trick.

    Keep in mind we want to keep the host system out of the
    LD_LIBRARY_PATH to make sure we won't inject any host DSOs (other
    than the GL/Cuda ones OFC) to the nix-built program.

    This function returns a dictionary containing the env variables
    supposed to be added to the current process down the line."""
    log_info("Nvidia routine begins")
    log_info("Setting up Nvidia cache directory")
    cache_dir = os.path.join(cache_dir, "nvidia")
    libs_dir = os.path.join(cache_dir, "lib")
    cuda_dir = os.path.join(cache_dir, "cuda")
    glx_dir = os.path.join(cache_dir, "glx")
    egl_dir = os.path.join(cache_dir, "egl-confs")
    cache_file_path = os.path.join(cache_dir, "cache.json")
    log_info(f"Nvidia libs dir: {libs_dir}")
    log_info(f"Nvidia cuda dir: {libs_dir}")
    os.makedirs(libs_dir, exist_ok=True)
    os.makedirs(cuda_dir, exist_ok=True)
    os.makedirs(glx_dir, exist_ok=True)
    os.makedirs(egl_dir, exist_ok=True)
    # Find Host DSOS
    log_info("Searching for the host DSOs")
    dsos: HostDSOs = HostDSOs(
        generic=resolve_libraries(dso_vendor_paths, NVIDIA_DSO_PATTERNS),
        cuda=resolve_libraries(dso_vendor_paths, CUDA_DSO_PATTERNS),
        glx=resolve_libraries(dso_vendor_paths, GLX_DSO_PATTERNS),
    )
    log_info("Caching and patching host DSOs")
    # Cache/Patch DSOs
    if not is_dso_cache_up_to_date(dsos, cache_file_path):
        log_info("The cache is not up to date, regenerating it")
        shutil.rmtree(cache_dir)
        os.makedirs(libs_dir, exist_ok=True)
        os.makedirs(cuda_dir, exist_ok=True)
        os.makedirs(glx_dir, exist_ok=True)
        os.makedirs(egl_dir, exist_ok=True)
        copy_and_patch_libs(list(dsos.generic.values()), libs_dir, libs_dir)
        copy_and_patch_libs(list(dsos.glx.values()), glx_dir, libs_dir)
        copy_and_patch_libs(list(dsos.cuda.values()), cuda_dir, libs_dir)
        log_info("Setting up NVIDIA-specific execution env variables.")
        with open(cache_file_path, "w", encoding="utf8") as f:
            f.write(dsos.to_json())
    else:
        log_info("The cache is up to date.")
    egl_config_files = generate_nvidia_egl_config_files(cache_dir, libs_dir, egl_dir)
    new_env = {}
    log_info(f"__GLX_VENDOR_LIBRARY_NAME = nvidia")
    new_env["__GLX_VENDOR_LIBRARY_NAME"] = "nvidia"
    log_info(f"__EGL_VENDOR_LIBRARY_DIRS = {egl_config_files}")
    new_env["__EGL_VENDOR_LIBRARY_DIRS"] = egl_config_files
    ld_library_path = os.environ.get("LD_LIBRARY_PATH", None)
    nv_ld_library_path = f"{cuda_dir}:{glx_dir}"
    ld_library_path = (
        nv_ld_library_path
        if ld_library_path is None
        else f"{nv_ld_library_path}:{ld_library_path}"
    )
    log_info(f"LD_LIBRARY_PATH = {ld_library_path}")
    new_env["LD_LIBRARY_PATH"] = ld_library_path
    return new_env


def exec_binary(bin_path: str, args: List[str]) -> None:
    """Replace the current python program with the program pointed by
    BIN_PATH.

    Sets the relevant libGLvnd env variables."""
    log_info(f"Execv-ing {bin_path}")
    log_info(f"Goodbye now.")
    os.execvp(bin_path, [bin_path] + args)


def main(args):
    start_time = time.time()
    home = os.path.expanduser("~")
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME", os.path.join(home, ".cache"))
    cache_dir = os.path.join(xdg_cache_home, "nix-gl-host")
    log_info(f'Using "{cache_dir}" as cache dir.')
    os.makedirs(cache_dir, exist_ok=True)
    if args.driver_directory:
        log_info(
            f"Retreiving DSOs from the specified directory: {args.driver_directory}"
        )
        host_dsos_paths: List[str] = [args.driver_directory]
    else:
        log_info("Retrieving DSOs from the load path.")
        host_dsos_paths: List[str] = get_ld_paths()
    new_env = nvidia_main(cache_dir, host_dsos_paths)
    os.environ.update(new_env)
    log_info(f"{time.time() - start_time} seconds elapsed since script start.")
    exec_binary(args.NIX_BINARY, args.ARGS)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="nixglhost-wrapper",
        description="Wrapper used to massage the host GL drivers to work with your nix-built binary.",
    )
    parser.add_argument(
        "-d",
        "--driver-directory",
        type=str,
        help="Use the driver libraries contained in this directory instead of discovering them from the load path.",
        default=None,
    )
    parser.add_argument(
        "NIX_BINARY",
        type=str,
        help="Nix-built binary you'd like to wrap.",
    )
    parser.add_argument(
        "ARGS",
        type=str,
        nargs="*",
        help="The args passed to the wrapped binary.",
    )
    args = parser.parse_args()
    ret = main(args)
    sys.exit(ret)
