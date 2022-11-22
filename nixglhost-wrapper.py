#!/usr/bin/env python3
import argparse
import os
import sys

IN_NIX_STORE = False

if IN_NIX_STORE:
    # The following paths are meant to be substituted by Nix at build
    # time.
    PATCHELF_PATH = "@patchelf-bin@"
else:
    PATCHELF_PATH = "patchelf"


def info_debug(string):
    """Prints STR to STDERR if the DEBUG environment variable is set"""
    if "DEBUG" in os.environ:
        print(f"[+] {string}", file=sys.stderr)


def patch_dso(dsoPath, ):
    raise "TODO patch_dso"


def find_vendor_dso():
    raise "TODO find_vendor_dso"


def exec_binary(args):
    raise "TODO exec_binary"


def main(args):
    home = os.path.expanduser("~")
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME", os.path.join(HOME, ".cache"))
    os.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="nixglhost-wrapper",
        description="Wrapper used to massage the host GL drivers to work with your nix-built binary.",
    )
    parser.add_argument(
        "GL_VENDOR_PATH",
        type=str,
        help="a path pointing to the directory containing your GL driver shared libraries",
    )
    parser.add_argument(
        "NIX_BINARY_AND_ARGS",
        type=str,
        nargs="+",
        help="Nix-built binary you'd like to wrap and its args. For instance: nixglhost-wrapper /usr/lib/nvidia opengl-exe --with --some --args",
    )
    args = parser.parse_args()
    main()
