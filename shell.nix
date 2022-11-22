{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  nativeBuildInputs = [
    pkgs.nixpkgs-fmt
    pkgs.python3Packages.black
    pkgs.python3Packages.mypy
  ];
}
