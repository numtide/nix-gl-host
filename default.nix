{ pkgs ? import <nixpkgs> { }, lib ? pkgs.lib }:

pkgs.stdenvNoCC.mkDerivation {
  pname = "nix-gl-host";
  version = "0.1";
  # TODO: filter that out
  src = lib.cleanSource ./.;
  nativeBuildInputs = [
    pkgs.nixpkgs-fmt
    pkgs.python3
    pkgs.python3Packages.black
    pkgs.nixpkgs-fmt
  ];


  meta.mainProgram = "nixglhost";
}
