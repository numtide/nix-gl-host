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

fn main() {
    let _cli_args = CLI::parse();
}
