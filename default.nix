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

  postCheck = ''
    black --check $out/bin/nixglhost
    nixpkgs-fmt --check *.nix
  '';

  installPhase = ''
    install -D -m0755 nixglhost-wrapper.py $out/bin/nixglhost
  '';
}
