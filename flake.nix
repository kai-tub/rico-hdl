{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    systems.url = "github:nix-systems/x86_64-linux";
    nix-filter.url = "github:numtide/nix-filter";
    devshell.url = "github:numtide/devshell";
    pre-commit-hooks.url = "github:cachix/pre-commit-hooks.nix";
    nix-appimage = {
      url = "github:ralismark/nix-appimage";
    };
  };
  outputs = {
    self,
    nixpkgs,
    systems,
    devshell,
    ...
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
          pre-commit-check = inputs.pre-commit-hooks.lib.${system}.run {
            src = ./.;
            hooks = {
              alejandra.enable = true;
              trim-trailing-whitespace.enable = true;
            };
          };
          rico-hdl-test-runner-check =
            pkgs.runCommandNoCC "rs-encoder-test-runner-check" {
              nativeBuildInputs = [self.packages.${system}.rico-hdl-test-runner];
            } ''
              ${lib.getExe self.packages.${system}.rico-hdl-test-runner} && touch $out
            '';
        }
        // self.packages.${system}
    );
    packages = eachSystem (system: let
      pkgs = pkgsFor.${system};
    in rec {
      default = rico-hdl;

      rico-hdl = pkgs.rico-hdl;

      rico-hdl-AppImage = inputs.nix-appimage.mkappimage.${system} {
        drv = rico-hdl;
        name = rico-hdl.name;
        entrypoint = pkgs.lib.getExe rico-hdl;
      };

      rico-hdl-docker = pkgs.dockerTools.buildLayeredImage {
        name = rico-hdl.pname;
        tag = "latest";
        contents = [rico-hdl];
        config = {
          Entrypoint = [
            "${pkgs.lib.getExe rico-hdl}"
          ];
        };
      };

      rico-hdl-docker-pusher = pkgs.writeShellApplication {
        name = "rico-hdl-docker-pusher";
        runtimeInputs = [pkgs.skopeo];
        text = ''
          # requires user to be logged in to the GitHub container registry
          # via `docker login ghcr.io`
          nix build .#rico-hdl-docker
          DOCKER_REPOSITORY="docker://ghcr.io/kai-tub/rico-hdl"
          skopeo --insecure-policy copy "docker-archive:result" "$DOCKER_REPOSITORY"
        '';
      };

      rico-hdl-test-runner = pkgs.writeShellApplication {
        name = "rico-hdl-test-runner";
        runtimeInputs = [
          rico-hdl
          (pkgs.python3.withPackages
            pythonTestDeps)
        ];
        text = ''
          export ENCODER_S1_PATH=${./integration_tests/tiffs/BigEarthNet/S1}
          export ENCODER_S2_PATH=${./integration_tests/tiffs/BigEarthNet/S2}
          export ENCODER_HYSPECNET_PATH=${./integration_tests/tiffs/HySpecNet-11k}
          export ENCODER_EXEC_PATH=${pkgs.lib.getExe rico-hdl}
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
        inherit (self.checks.${system}.pre-commit-check) shellHook;
        nativeBuildInputs = buildPackage.nativeBuildInputs;
        buildInputs =
          buildPackage.buildInputs
          ++ self.checks.${system}.pre-commit-check.enabledPackages
          ++ (with pkgs; [
            # glibc
            rustc
            cargo
            rustfmt
            rust-analyzer
            cargo-flamegraph
            fd
          ]);
        BINDGEN_EXTRA_CLANG_ARGS = [
          ''
            -I"${pkgs.llvmPackages_latest.libclang.lib}/lib/clang/${pkgs.llvmPackages_latest.libclang.version}/include"''
        ];
        LIBCLANG_PATH =
          pkgs.lib.makeLibraryPath
          [pkgs.llvmPackages_latest.libclang.lib];
      };
      py = pkgs.devshell.mkShell {
        packages = [
          (pkgs.python312.withPackages
            (ps: (with ps; [
              # jupyter
              safetensors
              lmdb
              rasterio
              ipython
              natsort
              more-itertools
              typer
              python-lsp-server
              python-lsp-ruff
              tqdm
              structlog
            ])))
        ];
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
            value = "${inputs.self.packages.${system}.rico-hdl-AppImage}";
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
