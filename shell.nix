{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  nativeBuildInputs = [
    pkgs.cargo
    pkgs.rustc
    pkgs.rust-analyzer
    pkgs.clippy
  ];
}
