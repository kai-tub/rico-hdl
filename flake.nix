{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    systems.url = "github:nix-systems/x86_64-linux";
    nix-filter.url = "github:numtide/nix-filter";
    devshell.url = "github:numtide/devshell";
  };
  outputs = {
    self,
    nixpkgs,
    systems,
    nix-filter,
    devshell,
  } @ inputs: let
    eachSystem = nixpkgs.lib.genAttrs (import systems);
    pkgsFor = eachSystem (system: (nixpkgs.legacyPackages.${system}.extend devshell.overlays.default));
    filter = nix-filter.lib;
  in {
    checks = eachSystem (system: let
      pkgs = pkgsFor.${system};
      lib = pkgs.lib;
    in {
      python_integration_test = let
        inp =
          self.packages.${system}.default;
      in
        # FUTURE: Add a wrapper to check if the AppImage works as expected!
        pkgs.runCommandNoCC "python_integration_test" {
          nativeBuildInputs = [
            inp
            (pkgs.python3.withPackages
              (ps: with ps; [numpy lmdb rasterio safetensors more-itertools pytest]))
          ];
        } ''
          export ENCODER_S1_PATH=${./tiffs/BigEarthNet/S1}
          export ENCODER_S2_PATH=${./tiffs/BigEarthNet/S1}
          export ENCODER_EXEC_PATH=${lib.getExe inp}
          echo "Running Python integration tests."
          pytest ${./test_python_integration.py} && touch $out
        '';
    });
    packages = eachSystem (system: let
      pkgs = pkgsFor.${system};
    in {
      default = pkgs.rustPlatform.buildRustPackage {
        pname = "encoder";
        version = "0.1.0";

        src = filter {
          root = ./.;
          include = ["src" ./Cargo.lock ./Cargo.toml];
        };
        cargoSha256 = "sha256-cFshuQTtCY/0G5klM3a9SdA9HCj7RexFAvSWZk3g6pg=";
        nativeBuildInputs = with pkgs; [
          pkg-config
          clang
          llvmPackages.bintools
        ];
        buildInputs = with pkgs; [
          # rustc & cargo already added by buildRustPackage
          gdalMinimal
        ];
        BINDGEN_EXTRA_CLANG_ARGS = [
          ''
            -I"${pkgs.llvmPackages_latest.libclang.lib}/lib/clang/${pkgs.llvmPackages_latest.libclang.version}/include"''
        ];
        LIBCLANG_PATH =
          pkgs.lib.makeLibraryPath
          [pkgs.llvmPackages_latest.libclang.lib];
        meta = {
          # FUTURE: Add the passthru tests here as well!
          # But then I should definitely figure out how to call it from the CLI...
          # passthru.tests = let
          #   inp =
          #     self.packages.${system}.default;
          # in "";
          mainProgram = "encoder";
        };
      };
    });

    devShells = eachSystem (system: let
      pkgs = pkgsFor.${system};
      buildPackage = inputs.self.packages.${system}.default;
    in {
      default = pkgs.mkShell {
        nativeBuildInputs = buildPackage.nativeBuildInputs;
        buildInputs =
          buildPackage.buildInputs
          ++ (with pkgs; [
            # glibc
            rustc
            cargo
            rustfmt
            rust-analyzer
            cargo-flamegraph
          ]);
        BINDGEN_EXTRA_CLANG_ARGS = [
          ''
            -I"${pkgs.llvmPackages_latest.libclang.lib}/lib/clang/${pkgs.llvmPackages_latest.libclang.version}/include"''
        ];
        LIBCLANG_PATH =
          pkgs.lib.makeLibraryPath
          [pkgs.llvmPackages_latest.libclang.lib];
      };
      test = pkgs.devshell.mkShell {
        env = [
          {
            name = "JUPYTER_PATH";
            value = "${pkgs.python3Packages.jupyterlab}/share/jupyter";
          }
          {
            name = "PYTHONPATH";
            prefix = "${pkgs.python3Packages.ipykernel}/${pkgs.python3.sitePackages}";
          }
          {
            name = "ENCODER_S1_PATH";
            value = "${./tiffs/BigEarthNet/S1}";
          }
          {
            name = "ENCODER_S2_PATH";
            value = "${./tiffs/BigEarthNet/S1}";
          }
          {
            name = "ENCODER_EXEC_PATH";
            value = "./results/bin/encoder";
            # value = "${lib.getExe inp}";
          }
        ];
        packages = [
          (
            # ATTENTION! Care has to be taken to ensure that the
            # safetensors python version matches the version used in the cargo.lock file!
            pkgs.python3.withPackages
            (ps: with ps; [jupyter ipython numpy lmdb rasterio safetensors more-itertools blosc2 pytest])
          )
        ];
      };
    });
  };
}
