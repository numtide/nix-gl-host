#!/usr/bin/env python3

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from glob import glob
from typing import List, Literal, Dict, Tuple, TypedDict, TextIO, Optional

IN_NIX_STORE = False
CACHE_VERSION = 3


if IN_NIX_STORE:
    # The following paths are meant to be substituted by Nix at build
    # time.
    PATCHELF_PATH = "@patchelf-bin@"
else:
    PATCHELF_PATH = "patchelf"


class ResolvedLib:
    """This data type encapsulate one host dynamically shared object
    together with some metadata helping us to uniquely identify it."""

    def __init__(
        self,
        name: str,
        dirpath: str,
        fullpath: str,
        last_modification: Optional[float] = None,
        size: Optional[int] = None,
    ):
        self.name: str = name
        self.dirpath: str = dirpath
        self.fullpath: str = fullpath
        if size is None or last_modification is None:
            stat = os.stat(fullpath)
            self.last_modification: float = stat.st_mtime
            self.size: int = stat.st_size
        else:
            self.last_modification = last_modification
            self.size = size

    def __repr__(self):
        return f"ResolvedLib<{self.name}, {self.dirpath}, {self.fullpath}, {self.last_modification}, {self.size}>"

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "dirpath": self.dirpath,
            "fullpath": self.fullpath,
            "last_modification": self.last_modification,
            "size": self.size,
        }

    def __hash__(self):
        return hash(
            (self.name, self.dirpath, self.fullpath, self.last_modification, self.size)
        )

    def __eq__(self, o):
        return (
            self.name == o.name
            and self.fullpath == o.fullpath
            and self.dirpath == o.dirpath
            and self.last_modification == o.last_modification
            and self.size == o.size
        )

    @classmethod
    def from_dict(cls, d: Dict):
        return ResolvedLib(
            d["name"], d["dirpath"], d["fullpath"], d["last_modification"], d["size"]
        )


class LibraryPath:
    """This data type encapsulates a directory containing some GL/Cuda
    dynamically shared objects."""

    def __init__(
        self,
        glx: List[ResolvedLib],
        cuda: List[ResolvedLib],
        generic: List[ResolvedLib],
        egl: List[ResolvedLib],
        path: str,
    ):
        self.glx = glx
        self.cuda = cuda
        self.generic = generic
        self.egl = egl
        self.path = path

    def __eq__(self, other):
        return (
            set(self.glx) == set(other.glx)
            and set(self.cuda) == set(other.cuda)
            and set(self.generic) == set(other.generic)
            and set(self.egl) == set(other.egl)
            and self.path == other.path
        )

    def __repr__(self):
        return f"LibraryPath<{self.path}>"

    def __hash__(self):
        return hash(
            (
                tuple(self.glx),
                tuple(self.cuda),
                tuple(self.generic),
                tuple(self.egl),
                self.path,
            )
        )

    def to_dict(self) -> Dict:
        return {
            "glx": [v.to_dict() for v in self.glx],
            "cuda": [v.to_dict() for v in self.cuda],
            "generic": [v.to_dict() for v in self.generic],
            "egl": [v.to_dict() for v in self.egl],
            "path": self.path,
        }

    @classmethod
    def from_dict(cls, d: Dict):
        return LibraryPath(
            glx=[ResolvedLib.from_dict(v) for v in d["glx"]],
            cuda=[ResolvedLib.from_dict(v) for v in d["cuda"]],
            generic=[ResolvedLib.from_dict(v) for v in d["generic"]],
            egl=[ResolvedLib.from_dict(v) for v in d["egl"]],
            path=d["path"],
        )


class CacheDirContent:
    """This datatype encapsulates all the dynamically shared objects
    living in the nix-gl-host cache. We mostly use it to serialize
    what's in the cache on the disk and compare this content to what
    we scanned in the host system."""

    def __init__(self, paths: List[LibraryPath], version: int = CACHE_VERSION):
        self.paths: List[LibraryPath] = paths
        self.version: int = CACHE_VERSION

    def to_json(self):
        d = {"paths": [p.to_dict() for p in self.paths], "version": self.version}
        return json.dumps(d, sort_keys=True)

    def __eq__(self, o):
        return self.version == o.version and set(self.paths) == set(o.paths)

    @classmethod
    def from_json(cls, j: str):
        d: Dict = json.loads(j)
        return CacheDirContent(
            version=d["version"], paths=[LibraryPath.from_dict(p) for p in d["paths"]]
        )


# The following regexes list has been figured out by looking at the
# output of nix-build -A linuxPackages.nvidia_x11 before running
# ls ./result/lib | grep -E ".so$".
#
# TODO: find a more systematic way to figure out these names *not
# requiring to build/fetch the nvidia driver at runtime*.
# TODO: compile the regexes
NVIDIA_DSO_PATTERNS = [
    "libGLESv1_CM_nvidia\.so.*$",
    "libGLESv2_nvidia\.so.*$",
    "libglxserver_nvidia\.so.*$",
    "libnvcuvid\.so.*$",
    "libnvidia-allocator\.so.*$",
    "libnvidia-cfg\.so.*$",
    "libnvidia-compiler\.so.*$",
    "libnvidia-eglcore\.so.*$",
    "libnvidia-encode\.so.*$",
    "libnvidia-fbc\.so.*$",
    "libnvidia-glcore\.so.*$",
    "libnvidia-glsi\.so.*$",
    "libnvidia-glvkspirv\.so.*$",
    "libnvidia-gpucomp\.so.*$",
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
    # Cannot find that one :(
    "libnvtegrahv\.so.*$",
    # Host dependencies required by the nvidia DSOs to properly
    # operate
    # libdrm
    "libdrm\.so.*$",
    # libffi
    "libffi\.so.*$",
    # libgbm
    "libgbm\.so.*$",
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

EGL_DSO_PATTERNS = [
    "libEGL_nvidia\.so.*$",
    "libnvidia-egl-wayland\.so.*$",
    "libnvidia-egl-gbm\.so.*$",
]


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
        print('WARNING: file "/etc/ld.so.conf" not found.', file=sys.stderr)
    if PREFIX:
        if os.path.exists(PREFIX + "/etc/ld.so.conf"):
            paths.extend(parse_ld_conf_file(PREFIX + "/etc/ld.so.conf"))
        else:
            print(
                'WARNING: file "' + PREFIX + '/etc/ld.so.conf" not found.',
                file=sys.stderr,
            )
        paths.extend(
            [
                PREFIX + "/lib",
                PREFIX + "/usr/lib",
                PREFIX + "/lib64",
                PREFIX + "/usr/lib64",
            ]
        )
    paths.extend(
        [
            "/lib",
            "/usr/lib",
            "/lib64",
            "/usr/lib64",
            "/run/opengl-driver/lib",
            "/usr/lib/wsl/lib",
        ]
    )
    return [path for path in paths if os.path.isdir(path)]


def resolve_libraries(path: str, files_patterns: List[str]) -> List[ResolvedLib]:
    """Scans the PATH directory looking for the files complying with
    the FILES_PATTERNS regexes list.

    Returns the list of the resolved DSOs."""
    libraries: List[ResolvedLib] = []

    def is_dso_matching_pattern(filename):
        for pattern in files_patterns:
            if re.search(pattern, filename):
                return True
        return False

    for fname in os.listdir(path):
        abs_file_path = os.path.abspath(os.path.join(path, fname))
        if os.path.isfile(abs_file_path) and is_dso_matching_pattern(abs_file_path):
            libraries.append(
                ResolvedLib(name=fname, dirpath=path, fullpath=abs_file_path)
            )
    return libraries


def copy_and_patch_libs(
    dsos: List[ResolvedLib], dest_dir: str, rpath: Optional[str] = None
) -> None:
    """Copies the graphic vendor DSOs to the cache directory before
    patchelf-ing them.

    The DSOs can dlopen each other. Sadly, we don't want any host
    libraries to the LD_LIBRARY_PATH to prevent polluting the nix
    binary env. The only option left is to patch their ELFs runpath to
    point to RPATH.

    We also don't want to directly modify the host DSOs. In the end,
    we first copy them to the user's personal cache directory, we then
    alter their runpath to point to the cache directory."""
    rpath = rpath if (rpath is not None) else dest_dir
    new_paths: List[str] = []
    for dso in dsos:
        basename = os.path.basename(dso.fullpath)
        newpath = os.path.join(dest_dir, basename)
        log_info(f"Copying and patching {dso} to {newpath}")
        shutil.copyfile(dso.fullpath, newpath)
        # Provide write permissions to ensure we can patch this binary.
        os.chmod(newpath, os.stat(dso.fullpath).st_mode | stat.S_IWUSR)
        new_paths.append(newpath)
    patch_dsos(new_paths, rpath)


def log_info(string: str) -> None:
    """Prints STR to STDERR if the DEBUG environment variable is
    set."""
    if "DEBUG" in os.environ:
        print(f"[+] {string}", file=sys.stderr)


def patch_dsos(dsoPaths: List[str], rpath: str) -> None:
    """Call patchelf to change the DSOS runpath with RPATH."""
    log_info(f"Patching {dsoPaths}")
    log_info(f"Exec: {PATCHELF_PATH} --set-rpath {rpath} {dsoPaths}")
    res = subprocess.run([PATCHELF_PATH, "--set-rpath", rpath] + dsoPaths)
    if res.returncode != 0:
        raise BaseException(
            f"Cannot patch {dsoPaths}. Patchelf exited with {res.returncode}"
        )


def generate_nvidia_egl_config_files(egl_conf_dir: str) -> None:
    """Generates a set of JSON files describing the EGL exec
    envirnoment to libglvnd.

    These configuration files will point to the EGL, wayland and GBM
    Nvidia DSOs. We're only specifying the DSOs names here to give the
    linker enough legroom to load the most appropriate DSO from the
    LD_LIBRARY_PATH."""

    def generate_egl_conf_json(dso):
        return json.dumps(
            {"file_format_version": "1.0.0", "ICD": {"library_path": dso}}
        )

    dso_paths = [
        ("10_nvidia.json", f"libEGL_nvidia.so.0"),
        ("10_nvidia_wayland.json", f"libnvidia-egl-wayland.so.1"),
        ("15_nvidia_gbm.json", f"libnvidia-egl-gbm.so.1"),
    ]

    for conf_file_name, dso_name in dso_paths:
        os.makedirs(egl_conf_dir, exist_ok=True)
        with open(
            os.path.join(egl_conf_dir, conf_file_name), "w", encoding="utf-8"
        ) as f:
            log_info(f"Writing {dso_name} conf to {egl_conf_dir}")
            f.write(generate_egl_conf_json(dso_name))


def is_dso_cache_up_to_date(dsos: CacheDirContent, cache_file_path: str) -> bool:
    """Check whether or not we need to update the cache.

    We keep what's in the cache through a JSON file stored at the root
    of the cache_dir. We consider a dynamically shared object to be up
    to date if its name, its full path, its size and last modification
    timestamp are equivalent."""
    log_info("Checking if the cache is up to date")
    if os.path.isfile(cache_file_path):
        with open(cache_file_path, "r", encoding="utf8") as f:
            try:
                cached_dsos: CacheDirContent = CacheDirContent.from_json(f.read())
            except:
                return False
            return dsos == cached_dsos
    return False


def scan_dsos_from_dir(path: str) -> Optional[LibraryPath]:
    """Look for the different kind of DSOs we're searching in a
    particular library path.
    This will match and hash the content of each object we're
    interested in."""
    generic = resolve_libraries(path, NVIDIA_DSO_PATTERNS)
    if len(generic) > 0:
        cuda = resolve_libraries(path, CUDA_DSO_PATTERNS)
        glx = resolve_libraries(path, GLX_DSO_PATTERNS)
        egl = resolve_libraries(path, EGL_DSO_PATTERNS)
        return LibraryPath(glx=glx, cuda=cuda, generic=generic, egl=egl, path=path)
    else:
        return None


def cache_library_path(
    library_path: LibraryPath, temp_cache_dir_root: str, final_cache_dir_root: str
) -> str:
    """Generate a cache directory for the LIBRARY_PATH host directory.

    This cache directory is mirroring the host directory containing
    the graphics card drivers. Its full name is hashed: it's an
    attempt to keep the final LD_LIBRARY_PATH reasonably sized.

    Returns the name of the cache directory created by this
    function to CACHE_DIR_ROOT."""
    # Hash Computation
    h = hashlib.sha256()
    h.update(library_path.path.encode("utf8"))
    path_hash: str = h.hexdigest()
    # Paths
    cache_path_root: str = os.path.join(temp_cache_dir_root, path_hash)
    lib_dir = os.path.join(cache_path_root, "lib")
    rpath_lib_dir = os.path.join(final_cache_dir_root, path_hash, "lib")
    cuda_dir = os.path.join(cache_path_root, "cuda")
    egl_dir = os.path.join(cache_path_root, "egl")
    glx_dir = os.path.join(cache_path_root, "glx")
    # Copy and patch DSOs
    for dsos, d in [
        (library_path.generic, lib_dir),
        (library_path.cuda, cuda_dir),
        (library_path.egl, egl_dir),
        (library_path.glx, glx_dir),
    ]:
        os.makedirs(d, exist_ok=True)
        if len(dsos) > 0:
            copy_and_patch_libs(dsos=dsos, dest_dir=d, rpath=rpath_lib_dir)
        else:
            log_info(f"Did not find any DSO to put in {d}, skipping copy and patching.")
    return path_hash


def generate_cache_ld_library_path(cache_paths: List[str]) -> str:
    """Generates the LD_LIBRARY_PATH colon-separated string pointing
    to the cached DSOs living inside the CACHE_PATHS.

    CACHE_PATH being a list pointing to the root of all the cached
    library paths.
    """
    ld_library_paths: List[str] = []
    for path in cache_paths:
        ld_library_paths = ld_library_paths + [
            f"{path}/lib",
            f"{path}/glx",
            f"{path}/cuda",
            f"{path}/egl",
        ]
    return ":".join(ld_library_paths)


def generate_cache_metadata(
    cache_dir: str, cache_content: CacheDirContent, cache_paths: List[str]
) -> str:
    """Generates the various cache metadata for a given CACHE_CONTENT
    and CACHE_PATHS in CACHE_DIR. Return the associated LD_LIBRARY_PATH.

    The metadata being:

    - CACHE_DIR/cache.json: json file containing all the paths info.
    - CACHE_DIR/ld_library_path: file containing the LD_LIBRARY_PATH
      to inject for the CACHE_PATHS.
    - CACHE_DIR/egl-confs: directory containing the various EGL
      confs."""
    cache_file_path = os.path.join(cache_dir, "cache.json")
    cached_ld_library_path = os.path.join(cache_dir, "ld_library_path")
    egl_conf_dir = os.path.join(cache_dir, "egl-confs")
    with open(cache_file_path, "w", encoding="utf8") as f:
        f.write(cache_content.to_json())
    nix_gl_ld_library_path = generate_cache_ld_library_path(cache_paths)
    log_info(f"Caching LD_LIBRARY_PATH: {nix_gl_ld_library_path}")
    with open(cached_ld_library_path, "w", encoding="utf8") as f:
        f.write(nix_gl_ld_library_path)
    generate_nvidia_egl_config_files(egl_conf_dir)
    return nix_gl_ld_library_path


def nvidia_main(
    cache_dir: str, dso_vendor_paths: List[str], print_ld_library_path: bool = False
) -> Dict:
    """Prepares the environment necessary to run a opengl/cuda program
    on a Nvidia graphics card. It is by definition really stateful.

    Roughly, we're going to:

    1. Setup the nvidia cache directory.
    2. Find the nvidia DSOs in the DSO_VENDOR_PATHS directories.
    3. Copy these DSOs to their appropriate cache directories.
    4. Generate the EGL configuration files.
    5. Patchelf the runpath of what needs to be patched.
    6. Generate the env variables the main process is supposed to set.

    Keep in mind we want to keep the host system out of the
    LD_LIBRARY_PATH to make sure we won't inject any host DSOs (other
    than the GL/Cuda ones OFC) to the nix-built program.

    We're isolating the main DSOs for GLX/EGL/Cuda in their own dirs,
    add add these directory to the LD_LIBRARY_PATH. We patch their
    runpaths to point to the generic cache dir, containing all the
    libraries we don't want to expose to the program we're wrapping.

    This function returns a dictionary containing the env variables
    supposed to be added to the current process down the line."""
    log_info("Nvidia routine begins")
    # Find Host DSOS
    log_info("Searching for the host DSOs")
    cache_content: CacheDirContent = CacheDirContent(paths=[])
    cache_file_path = os.path.join(cache_dir, "cache.json")
    lock_path = os.path.join(os.path.split(cache_dir)[0], "nix-gl-host.lock")
    cached_ld_library_path = os.path.join(cache_dir, "ld_library_path")
    paths = get_ld_paths()
    egl_conf_dir = os.path.join(cache_dir, "egl-confs")
    nix_gl_ld_library_path: Optional[str] = None
    # Cache/Patch DSOs
    #
    # We need to be super careful about race conditions here. We're
    # using a file lock to make sure only one nix-gl-host instance can
    # access the cache at a time.
    #
    # If the cache is locked, we'll wait until the said lock is
    # released. The lock will always be released when the lock FD get
    # closed, IE. when we'll get out of this block.
    with open(lock_path, "w") as lock:
        log_info("Acquiring the cache lock")
        fcntl.flock(lock, fcntl.LOCK_EX)
        log_info("Cache lock acquired")
        for path in paths:
            res = scan_dsos_from_dir(path)
            if res:
                cache_content.paths.append(res)
        if not is_dso_cache_up_to_date(
            cache_content, cache_file_path
        ) or not os.path.isfile(cached_ld_library_path):
            log_info("The cache is not up to date, regenerating it")
            # We're building first the cache in a temporary directory
            # to make sure we won't end up with a partially
            # populated/corrupted nix-gl-host cache.
            with tempfile.TemporaryDirectory() as tmp_cache:
                tmp_cache_dir = os.path.join(tmp_cache, "nix-gl-host")
                os.makedirs(tmp_cache_dir)
                cache_paths: List[str] = []
                for p in cache_content.paths:
                    log_info(f"Caching {p}")
                    cache_paths.append(cache_library_path(p, tmp_cache_dir, cache_dir))
                # Pointing the LD_LIBRARY_PATH to the final destination
                # instead of the tmp dir.
                cache_absolute_paths = [os.path.join(cache_dir, p) for p in cache_paths]
                nix_gl_ld_library_path = generate_cache_metadata(
                    tmp_cache_dir, cache_content, cache_absolute_paths
                )
                # The temporary cache has been successfully populated,
                # let's mv it to the actual nix-gl-host cache.
                # Note: The move operation is atomic on linux.
                log_info(f"Mv {tmp_cache_dir} to {cache_dir}")
                if os.path.exists(cache_dir):
                    shutil.rmtree(cache_dir)
                shutil.move(tmp_cache_dir, os.path.split(cache_dir)[0])
        else:
            log_info("The cache is up to date, re-using it.")
            with open(cached_ld_library_path, "r", encoding="utf8") as f:
                nix_gl_ld_library_path = f.read()
    log_info("Cache lock released")

    assert nix_gl_ld_library_path, "The nix-host-gl LD_LIBRARY_PATH is not set"
    log_info(f"Injecting LD_LIBRARY_PATH: {nix_gl_ld_library_path}")
    new_env = {}
    log_info(f"__GLX_VENDOR_LIBRARY_NAME = nvidia")
    new_env["__GLX_VENDOR_LIBRARY_NAME"] = "nvidia"
    log_info(f"__EGL_VENDOR_LIBRARY_DIRS = {egl_conf_dir}")
    new_env["__EGL_VENDOR_LIBRARY_DIRS"] = egl_conf_dir
    ld_library_path = os.environ.get("LD_LIBRARY_PATH", None)
    if print_ld_library_path:
        print(nix_gl_ld_library_path)
    ld_library_path = (
        nix_gl_ld_library_path
        if ld_library_path is None
        else f"{nix_gl_ld_library_path}:{ld_library_path}"
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
    os.makedirs(cache_dir, exist_ok=True)
    log_info(f'Using "{cache_dir}" as cache dir.')
    if args.driver_directory:
        log_info(
            f"Retreiving DSOs from the specified directory: {args.driver_directory}"
        )
        host_dsos_paths: List[str] = [args.driver_directory]
    else:
        log_info("Retrieving DSOs from the load path.")
        host_dsos_paths: List[str] = get_ld_paths()
    new_env = nvidia_main(cache_dir, host_dsos_paths, args.print_ld_library_path)
    log_info(f"{time.time() - start_time} seconds elapsed since script start.")
    if args.NIX_BINARY:
        os.environ.update(new_env)
        exec_binary(args.NIX_BINARY, args.ARGS)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="nixglhost",
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
        "-p",
        "--print-ld-library-path",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Print the GL/Cuda LD_LIBRARY_PATH env you should add to your environment.",
    )
    parser.add_argument(
        "NIX_BINARY",
        type=str,
        nargs="?",
        help="Nix-built binary you'd like to wrap.",
        default=None,
    )
    parser.add_argument(
        "ARGS",
        type=str,
        nargs="*",
        help="The args passed to the wrapped binary.",
        default=None,
    )
    args = parser.parse_args()
    if args.print_ld_library_path and args.NIX_BINARY:
        print(
            "ERROR: -p and NIX_BINARY are both set. You have to choose between one of these options.",
            file=sys.stderr,
        )
        print("       run nixglhost --help for more informations. ", file=sys.stderr)
        sys.exit(1)
    elif not args.print_ld_library_path and not args.NIX_BINARY:
        print("ERROR: Please set the NIX_BINARY you want to run.", file=sys.stderr)
        print("       run nixglhost --help for more informations. ", file=sys.stderr)
        sys.exit(1)
    ret = main(args)
    sys.exit(ret)
