use std::{time::SystemTime, path::{PathBuf}};

use clap::Parser;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct CLI {
    ///Use the driver libraries contained in this directory instead of discovering them from the load path.
    #[arg(short, long)]
    driver_directory: Option<String>,

    ///Print the GL/Cuda LD_LIBRARY_PATH env you could add to your environment. DISCOURAGED!
    #[arg(short,long, default_value_t=false)]
    print_ld_library_path: bool,

    ///Nix-built binary you want to wrap.
    nix_binary_path: String,

    ///The args passed to the wrapped binary.
    args: Vec<String>
}

/// Represents a GPU host library.
///
/// We uniquely identify a library through its fullpath, the last
/// modification date and its length.
///
/// We used to content-adress those, but hasing all these files turned
/// out slowing down the wrapper quite significantly.
struct ResolvedLib {
    name: String,
    fullpath: PathBuf,
    last_modification: SystemTime,
    len: u64
}

/// Represents a host library path entry. This entry can contain many
/// GPU dynamic libraries.
struct HostLibraryPath {
    fullpath: PathBuf,
    /// GLX-related libraries contained in this library path entry.
    glx: Vec<ResolvedLib>,
    /// EGL-related libraries contained in this library path entry.
    egl: Vec<ResolvedLib>,
    /// Cuda-related libraries contained in this library path entry.
    cuda: Vec<ResolvedLib>,
    /// Generic/helper libraries contained in this library path entry.
    generic: Vec<ResolvedLib>,
}

/// Encapsulates all the dynamically shared objects living in the
/// nix-gl-host cache.
///
/// We mostly use it to serialize what's in the cache on the disk and
/// compare this content to what we scanned in the host system.
struct CacheDirContent {
    paths: Vec<HostLibraryPath>
}

fn main() {
    let _cli_args = CLI::parse();
}
