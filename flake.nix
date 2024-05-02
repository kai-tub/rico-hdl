{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    systems.url = "github:nix-systems/x86_64-linux";
    nix-filter.url = "github:numtide/nix-filter";
    devshell.url = "github:numtide/devshell";
    nix-appimage = {
      url = "github:ralismark/nix-appimage";
      # inputs.nixpkgs.follows = "nixpkgs";
    };
  };
  outputs = {
    self,
    nixpkgs,
    systems,
    nix-filter,
    nix-appimage,
    devshell,
  } @ inputs: let
    eachSystem = nixpkgs.lib.genAttrs (import systems);
    pkgsFor = eachSystem (system: (nixpkgs.legacyPackages.${system}.extend devshell.overlays.default));
    filter = nix-filter.lib;
    pythonTestDeps = ps: with ps; [numpy lmdb rasterio safetensors more-itertools pytest];
  in {
    checks = eachSystem (system: let
      pkgs = pkgsFor.${system};
      lib = pkgs.lib;
      # put = package-under-test
      mk_integration_test = name: put:
        pkgs.runCommandNoCC name {
          nativeBuildInputs = [
            put
            (pkgs.python3.withPackages
              pythonTestDeps)
          ];
        } ''
          export ENCODER_S1_PATH=${./tiffs/BigEarthNet/S1}
          export ENCODER_S2_PATH=${./tiffs/BigEarthNet/S2}
          export ENCODER_EXEC_PATH=${lib.getExe put}
          echo "Running Python integration tests."
          pytest ${./test_python_integration.py} && touch $out
        '';
    in {
      python_integration_test =
        mk_integration_test "python_integration_test" self.packages.${system}.default;
      # FUTURE: Add a wrapper to check if the AppImage works as expected!
      # Much harder than I thought. As fuse isn't available inside of the build environment,
      # the appimage cannot be executed. Unpacking it should be possible but after spending way
      # too much time trying to get it working, I am giving up, as it seems like the nested nix
      # store inside of the squashfs root and the permissions seem to generate quite a few issues.
      # a =
      #   mk_integration_test "appimage_python_integration_test" self.packages.${system}.appImage;
    });
    packages = eachSystem (system: let
      pkgs = pkgsFor.${system};
    in rec {
      appImage = let
        image = inputs.nix-appimage.mkappimage.x86_64-linux {
          drv = default;
          name = default.name;
          entrypoint = pkgs.lib.getExe default;
        };
      in
        pkgs.runCommandNoCC "encoder-appimage" {meta.mainProgram = "encoder.AppImage";} ''
          mkdir -p $out/bin
          ln -s ${image} $out/bin/encoder.AppImage
        '';
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
            value = "./tiffs/BigEarthNet/S1";
          }
          {
            # seems to be some permission issues with walkdir
            # if I use ${./tiffs/...}
            # The permission all look good under the nix store
            # and copying from the directory to the local directory
            # also works
            name = "ENCODER_S2_PATH";
            value = "./tiffs/BigEarthNet/S2";
          }
          {
            name = "ENCODER_EXEC_PATH";
            # value = "./results/bin/encoder";
            value = "${pkgs.lib.getExe inputs.self.packages.${system}.appImage}";
          }
          {
            name = "RUST_BACKTRACE";
            value = "1";
          }
        ];
        packages = [
          (
            # ATTENTION! Care has to be taken to ensure that the
            # safetensors python version matches the version used in the cargo.lock file!
            pkgs.python3.withPackages
            (ps: (pythonTestDeps ps) ++ (with ps; [jupyter ipython more-itertools blosc2]))
          )
        ];
      };
    });
  };
}
