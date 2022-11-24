self: super:
{
  libglvnd = super.libglvnd.overrideAttrs (old: {
    src = super.fetchFromGitHub {
      owner = "NinjaTrappeur";
      repo = "libglvnd";
      rev = "f4dff011f78ecd5a69871d4a8ddf3c742de5f621";
      sha256 = "sha256-57awDiR9DaFTGe8J4ed89Xm3Fc4/OM6qflsuHqx9mxE=";
    };
  });
}
