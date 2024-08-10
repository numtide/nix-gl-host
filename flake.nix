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
      eachSystem = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      packages = eachSystem (pkgs: {
        default = import ./. { inherit pkgs; };
      });

      defaultPackage = eachSystem (pkgs: self.packages.${pkgs.system}.default);

      devShell = eachSystem (pkgs:
        pkgs.callPackage ./shell.nix { }
      );

      formatter = eachSystem (pkgs: pkgs.nixpkgs-fmt);

      checks = self.packages;
    };
}
