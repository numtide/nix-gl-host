{
  description = "Gluing host OpenGL drivers to a Nix-built binary";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  outputs =
    { self
    , nixpkgs
    }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f system);
      pkgs = system: import nixpkgs {
        inherit system;
        overlays = [ self.overlays.default ];
      };
    in
    {
      defaultPackage = forAllSystems (system: import ./default.nix { pkgs = pkgs system; });

      overlays.default = import ./overlays/nixpkgs.nix;

      legacyPackages = forAllSystems (system: (pkgs system));

      devShell = forAllSystems (system:
        nixpkgs.legacyPackages.${system}.callPackage ./shell.nix { }
      );

      formatter = forAllSystems (system:
        nixpkgs.legacyPackages.${system}.nixpkgs-fmt
      );

    };
}
