# NixGLHost - Nix OpenGL/Cuda wrapper

> Current status: alpha

Run OpenGL/Cuda programs built with Nix, on all[*] Linux distributions.

`*` - see the [support Matrix](#support-matrix)

# Why you may need NixGLHost?

Nix is great as a software distribution mechanism. It allows packaging a software once and distribute it securely to all Linux distributions. Because all the dependencies are bundled with the software, it doesn't suffer from incompatible Glibc version issues that other software might have.

Unfortunately while the previous statement is generally true, it breaks down when using programs depending on 3D drivers such as OpenGL or Cuda. Unlike with the Kernel, the interface to interact with the GPU is defined in the driver software, and that is dynamic depending on which host, and version of the driver is running.

This is where NixGLHost comes in handy. NixGLHost is a wrapper around your program that dynamically scans your host Linux system (Ubuntu, Fedora, etc.) and looks for the OpenGL/Cuda drivers. And then makes it available to use to to the Nix-built binary. It aims at solving this problem once and for all.

# Getting Started

There are several options to use NixglHost, and the one you choose depends on the way you want to specify the path.

## Automatic Driver Directory Detection (RECOMMENDED)

You can run `my-gl-program` and re-use your host distribution OpenGL/Cuda setup simply with:

```console
$ nixglhost my-gl-program
```

When invoked like above, `nixglhost` will scan your host library path and look for the relevant driver libraries to use.

## Explicitly Pointing to the Driver Directory

If the driver libraries auto-discovery system fails on your setup, you can explicitly point to the directory containing your driver libraries using the `--driver-directory` or `-d` command line flags.

For instance:

```console
$ nixglhost -d /usr/lib/x86_64-linux-gnu my-gl-program
```

## Global Library Path Export (⚠️ DISCOURAGED ⚠️)

Finally, you can also print the directories you should inject to your `LD_LIBRARY_PATH` to run an OpenGL program using the `--print-ld-library-path` or `-p` flag:

```console
$ LD_LIBRARY_PATH=$(nixglhost -p):$LD_LIBRARY_PATH my-gl-program
```

⚠️ WARNING: this feature is a major footgun.

It exists and is documented because you may not have any other options in some situations. However, you should always try to keep the dependency injection as close to the program as possible.

This means that you should always prefer wrapping the dependencies to a single binary rather than globally exporting them to the global execution environment.

# State of the project

We want to work with the community to integrate this work upstream. The current version demonstrates that solving this problem is possible but before adding more platforms to it, we believe that it would be good to 

## Support Matrix

Currently, this project supports the following features:

| Driver             | GLX    | EGL  | Cuda | OpenCL |
|--------------------|--------|------|------|--------|
| Proprietary Nvidia | ✅     | ✅   | ✅   | 🚫     |
| Mesa               | 🚫     | 🚫   | 🚫   | 🚫     |
| Nouveau            | 🚫     | 🚫   | 🚫   | 🚫     |
| Proprietary AMD    | 🚫     | 🚫   | 🚫   | 🚫     |

It has been tested on the following distributions:

| Distribution | Status |
|--------------|--------|
| Ubuntu 20.04 | ✅     |
| Ubuntu 22.04 | ✅     |

If you require more platforms to be supported, [get in touch with us](https://numtide.com/contact).

# Troubleshooting

## Debug Mode

You can enable the debug tracing of NixGLHost by setting the DEBUG environment variable.

```console
$ DEBUG=1 nixglhost my-gl-program
```

## Known error messages

If you are seeing the following error messages, your program isn't wrapped
with `nixglhost` yet.

OpenGL:
```
name of display: localhost:10.0
Error: couldn't find RGB GLX visual or fbconfig
```

EGL:
```
EGLUT: failed to initialize EGL display
```

# Previous Work

This works has drawn inspiration from [NixGL](https://github.com/guibou/nixGL). NixGL solves the same issue with a different approach. Instead of re-using the host GL libraries, it uses the Nixpkgs-provided ones to wrap the OpenGL program. With this approach, the graphic drivers are also distributed through Nix. The Nix closure is fully contained. It’s a safer approach as you’re less likely to stumble upon any DSO ABI incompatibility.

However, this explicit approach comes with tradeoff: you need to build one Nix closure for each graphic driver you plan to support. That also includes versions of the driver. This makes the deployment more complex: for each machine, you need to figure
out which GPU-specific Nix closure to use.

How we see it, NixGL is best adapted for closed environment where the target hosts are under the author's control. NixGlHost is best adapted for open environments where the author doesn't control who is going to use their program.

## Design

See the [INTERNALS.md](INTERNALS.md) document.

# Contributing

⚠️ WARNING: we won't accept new driver contributions at this time.

The code needs to be cleaned up and rewritten before scaling to more drivers.

If you require more platforms to be supported, [get in touch with us](https://numtide.com/contact).

# Authors/Maintainers

- [Flokli](https://flokli.de/)
- [Ninjatrappeur](https://alternativebit.fr/)
