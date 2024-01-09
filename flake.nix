{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    systems.url = "github:nix-systems/x86_64-linux";
    devenv = {
      # https://github.com/cachix/devenv/issues/756
      url = "github:cachix/devenv/6a30b674fb5a54eff8c422cc7840257227e0ead2";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };
  outputs = { self, nixpkgs, systems, devenv }:
    let
      eachSystem = nixpkgs.lib.genAttrs (import systems);
      pkgsFor = eachSystem (system: (nixpkgs.legacyPackages.${system}));
    in {
      devShells = eachSystem (system:
        let pkgs = pkgsFor.${system};
        in {
          default = pkgs.mkShell {
            buildInputs = with pkgs; [
              pkg-config
              gdal
              clang
              glibc
              llvmPackages.bintools
              rustc
              cargo
              rustfmt
              rust-analyzer
              proj
            ];
            BINDGEN_EXTRA_CLANG_ARGS = [
              ''
                -I"${pkgs.llvmPackages_latest.libclang.lib}/lib/clang/${pkgs.llvmPackages_latest.libclang.version}/include"''
            ];
            LIBCLANG_PATH = pkgs.lib.makeLibraryPath
              [ pkgs.llvmPackages_latest.libclang.lib ];
          };

        });
    };
}
