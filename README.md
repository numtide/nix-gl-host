# NixGLHost

Running OpenGL Nix-built binaries on a foreign Linux distro is quite often a challenge. NixGLHost is gluing your nix-built binaries to the host OpenGL implementation.

# NixGLHost Approach

TODO before release, rephrase this, explain further. Clone the blog post in this section?

1. Patched libGLVnd to load vendor DSOs from a custom location, not relying on the library path.
1. Copy the host vendor DSOs to a nix-tmp location.
1. Modify the vendor DSOs runpath to point to the place where the vendor libs live.
1. Wrap the nix-built binary, inject the libGLVnd-specific env variables to point to the patched vendor lib dir.

# Support

- [ ] Proprietary Nvidia
  - [ ] GLX
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
