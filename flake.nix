{
  description = "Gluing native OpenGL drivers";
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
    in
    {
      defaultPackage = forAllSystems (system:
        import ./default.nix {
          pkgs = import nixpkgs { inherit system; };
        });
      devShell = forAllSystems (system:
        nixpkgs.legacyPackages.${system}.callPackage ./shell.nix { }
      );

      formatter = forAllSystems (system:
        nixpkgs.legacyPackages.${system}.nixpkgs-fmt
      );
    };
}
