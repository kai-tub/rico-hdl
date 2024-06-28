{
  lib,
  nix-filter,
  rustPlatform,
  pkg-config,
  clang,
  llvmPackages,
  gdalMinimal,
  llvmPackages_latest,
  version ? "git",
}:
rustPlatform.buildRustPackage {
  pname = "rico-hdl";
  inherit version;

  src = nix-filter {
    root = ../.;
    include = ["src" "Cargo.lock" "Cargo.toml"];
  };
  # cargoLock.lockFile = ../Cargo.lock;
  # https://github.com/NixOS/nixpkgs/pull/113176
  cargoDepsName = "rico-hdl";
  cargoHash = "sha256-1Ufs/MLlL8oAm4xDzte0lv8+HzfV2z1dYjSrP7Iaao4=";
  nativeBuildInputs = [
    pkg-config
    clang
    llvmPackages.bintools
  ];
  buildInputs = [
    # rustc & cargo already added by buildRustPackage
    gdalMinimal
  ];
  BINDGEN_EXTRA_CLANG_ARGS = [
    ''
      -I"${llvmPackages_latest.libclang.lib}/lib/clang/${llvmPackages_latest.libclang.version}/include"''
  ];
  LIBCLANG_PATH =
    lib.makeLibraryPath
    [llvmPackages_latest.libclang.lib];
  meta = {
    description = "A deep-learning tensor encoder tool for remote sensing datasets.";
    homepage = "https://github.com/kai-tub/rico-hdl";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [kai-tub];
    mainProgram = "rico-hdl";
  };
}
