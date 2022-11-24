# NixGLHost

Running OpenGL Nix-built binaries on a foreign Linux distro is quite often a challenge. NixGLHost glues a nix-built program to your host system graphics drivers.

Current status: experimental.

# How to Use

First of all, build your Opengl program with our custom libglvnd. You can use this project's flake default overlay as a convenience. Let's build glxgears, living in the glxinfo derivation:

```sh
nix build .#glxinfo
```

Let say that your host graphics drivers are stored in `/lib/x86_64-linux-gnu/`. TODO: explain how to figure out where are the host graphic drivers.

You can run glxgear with your host graphics driver using:

```sh
PATH=$(nix build --print-out-paths)/bin:$PATH
nixglhost /lib/x86_64-linux-gnu $(nix build  --print-out-paths .#glxinfo)/bin/glxgears
```

# NixGLHost Approach

Re-using the host graphics dynamic libraries turned out being quite challenging.

NixGLHost relies on a [patched libGLvnd](https://github.com/NinjaTrappeur/libglvnd/commit/f4dff011f78ecd5a69871d4a8ddf3c742de5f621) to inject the host DSOs without polluting the `LD_LIBRARY_PATH`. You can use the `./overlays/nixpkgs.nix` nixpkgs overlay (exposed via `flake.nix` for external projects) to build a binary with this custom libglvnd.

Here's how everything works:

1. Detect the host vendor graphic DSOs via some heuristics.
1. Copy the host vendor DSOs to a cache location.
1. Modify the cached DSOs runpath to point to the cache. The graphics DSOs depend on each other and won't be able to find each other using the default Nix `LD_LIBRARY_PATH`.
1. Inject the libGLVnd-specific env variables to point to the patched vendor lib.
1. Execute the wrapped binary.

This approach won't affect the Nix hermiticity: the only "external" DSOs loaded to the Nix-built program are the host-specific graphics drivers.

# Support

- [-] Proprietary Nvidia
  - [x] GLX
  - [ ] EGL
  - [ ] Cuda
  - [ ] OpenCL
- [ ] Mesa
  - [ ] GLX
  - [ ] EGL
  - [ ] OpenCL

# Alternative Approaches

-  [NixGL](https://github.com/guibou/nixGL): tries to auto detect the host vendor driver, download it again, store it in the nix-store then wraps the nix-built binary and inject the downloaded vendor driver through `LD_LIBRARY_PATH`.

# Authors/Maintainers

- [Flokli](https://flokli.de/)
- [Ninjatrappeur](https://alternativebit.fr/)
