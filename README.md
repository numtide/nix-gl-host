# NixGLHost

Running OpenGL/Cuda/OpenCL Nix-built binaries on a foreign Linux distro is quite often a challenge. These programs are relying on some host-specific graphics drivers at runtime. These drivers are host-specific, it is obviously impossible to distribute the drivers for each and every hosts setup through a pre-defined generic nix closure.

NixGLHost solves this issue by re-using your host system graphics drivers. It copies them to an isolated environment and inject the said environment to the Nix runtime closure.

Current status: experimental.

# How to Use

All you have to do is to wrap your nix-built OpenGL/Cuda program with `nixglhost`:

For instance, let's say you want to run `my-gl-program`, a `nix-built` program on your favorite distribution. All you'll have to do is:

```
nixglhost my-gl-program
```

## Example

Let's nix-build glxgears, living in the glxinfo Nixpkgs derivation then execute it with nixglhost.

```sh
cd $thisRepoCheckout
PATH=$(nix build --print-out-paths)/bin:$PATH
nixglhost $(nix build  --print-out-paths .#glxinfo)/bin/glxgears
```

# Internals

You can read the [INTERNALS.md](INTERNALS.md) file to learn how exactly `NixGLHost` works.

# Support

- [-] Proprietary Nvidia
  - [x] GLX
  - [x] EGL
  - [x] Cuda
  - [ ] OpenCL
- [ ] Mesa
  - [ ] GLX
  - [ ] EGL
  - [ ] OpenCL

# Alternative Approaches

-  [NixGL](https://github.com/guibou/nixGL): tries to auto detect the host vendor driver type/version, then download/install it from its Nixpkgs derivation.

# Authors/Maintainers

- [Flokli](https://flokli.de/)
- [Ninjatrappeur](https://alternativebit.fr/)
