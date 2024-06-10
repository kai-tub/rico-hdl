{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    systems.url = "github:nix-systems/x86_64-linux";
    nix-filter.url = "github:numtide/nix-filter";
    devshell.url = "github:numtide/devshell";
    nix-appimage = {
      url = "github:ralismark/nix-appimage";
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
    pkgsFor = eachSystem (system: ((nixpkgs.legacyPackages.${system}.extend devshell.overlays.default).extend self.overlays.default));
    pythonTestDeps = ps: with ps; [numpy lmdb rasterio safetensors more-itertools pytest];
  in {
    overlays = import ./nix/overlays.nix {
      inherit inputs;
      lib = nixpkgs.lib;
    };
    formatter = eachSystem (system: pkgsFor.${system}.alejandra);
    checks = eachSystem (
      system: let
        pkgs = pkgsFor.${system};
        lib = pkgs.lib;
      in
        {
          rs-tensor-encoder-test-runner-check =
            pkgs.runCommandNoCC "rs-encoder-test-runner-check" {
              nativeBuildInputs = [self.packages.${system}.rs-tensor-encoder-test-runner];
            } ''
              ${lib.getExe self.packages.${system}.rs-tensor-encoder-test-runner} && touch $out
            '';
        }
        // self.packages.${system}
    );
    packages = eachSystem (system: let
      pkgs = pkgsFor.${system};
    in rec {
      default = rs-tensor-encoder;

      rs-tensor-encoder = pkgs.rs-tensor-encoder;

      rs-tensor-encoder-AppImage = inputs.nix-appimage.mkappimage.${system} {
        drv = rs-tensor-encoder;
        name = rs-tensor-encoder.name;
        entrypoint = pkgs.lib.getExe rs-tensor-encoder;
      };

      rs-tensor-encoder-docker = pkgs.dockerTools.buildLayeredImage {
        name = rs-tensor-encoder.pname;
        tag = "latest";
        contents = [rs-tensor-encoder];
        config = {
          Entrypoint = [
            "${pkgs.lib.getExe rs-tensor-encoder}"
          ];
        };
      };

      rs-tensor-encoder-docker-pusher = pkgs.writeShellApplication {
        name = "rs-tensor-encoder-docker-pusher";
        runtimeInputs = [pkgs.skopeo];
        text = ''
          # requires user to be logged in to the GitHub container registry
          # via `docker login ghcr.io`
          nix build .#rs-tensor-encoder-docker
          DOCKER_REPOSITORY="docker://ghcr.io/kai-tub/rs-tensor-encoder"
          skopeo --insecure-policy copy "docker-archive:result" "$DOCKER_REPOSITORY"
        '';
      };

      rs-tensor-encoder-test-runner = pkgs.writeShellApplication {
        name = "rs-tensor-encoder-test-runner";
        runtimeInputs = [
          rs-tensor-encoder
          (pkgs.python3.withPackages
            pythonTestDeps)
        ];
        text = ''
          export ENCODER_S1_PATH=${./integration_tests/tiffs/BigEarthNet/S1}
          export ENCODER_S2_PATH=${./integration_tests/tiffs/BigEarthNet/S2}
          export ENCODER_HYSPECNET_PATH=${./integration_tests/tiffs/HySpecNet-11k}
          export ENCODER_EXEC_PATH=${pkgs.lib.getExe rs-tensor-encoder}
          echo "Running Python integration tests."
          pytest ${./integration_tests/test_python_integration.py} && echo "Success!"
        '';
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
            value = "./integration_tests/tiffs/BigEarthNet/S1";
          }
          {
            # seems to be some permission issues with walkdir
            # if I use ${./tiffs/...}
            # The permission all look good under the nix store
            # and copying from the directory to the local directory
            # also works
            name = "ENCODER_S2_PATH";
            value = "./integration_tests/tiffs/BigEarthNet/S2";
          }
          {
            name = "ENCODER_EXEC_PATH";
            # value = "./results/bin/encoder";
            value = "${inputs.self.packages.${system}.rs-tensor-encoder-AppImage}";
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
