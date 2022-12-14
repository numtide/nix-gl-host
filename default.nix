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

  postFixup = ''
    substituteInPlace $out/bin/nixglhost \
        --replace "@patchelf-bin@" "${pkgs.patchelf}/bin/patchelf" \
        --replace "IN_NIX_STORE = False" "IN_NIX_STORE = True"
    patchShebangs $out/bin/nixglhost
  '';

  doCheck = true;

  checkPhase = ''
    black --check src/*.py
    nixpkgs-fmt --check *.nix
    python src/nixglhost_test.py
  '';

  installPhase = ''
    install -D -m0755 src/nixglhost.py $out/bin/nixglhost
  '';
}
