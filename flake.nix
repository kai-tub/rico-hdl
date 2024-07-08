{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    systems.url = "github:nix-systems/x86_64-linux";
    nix-filter.url = "github:numtide/nix-filter";
    devenv = {
      url = "github:cachix/devenv";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pre-commit-hooks.url = "github:cachix/pre-commit-hooks.nix";
    nix-appimage = {
      url = "github:ralismark/nix-appimage";
    };
    poetry2nix.url = "github:nix-community/poetry2nix";
  };
  outputs = {
    self,
    nixpkgs,
    systems,
    ...
  } @ inputs: let
    eachSystem = nixpkgs.lib.genAttrs (import systems);
    # pkgsFor = eachSystem (system: ((nixpkgs.legacyPackages.${system}.extend devshell.overlays.default).extend self.overlays.default));
    pkgsFor = eachSystem (system: (nixpkgs.legacyPackages.${system}));
    pythonTestDeps = ps: with ps; [numpy lmdb rasterio safetensors more-itertools pytest];
  in {
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
      inherit (inputs.poetry2nix.lib.mkPoetry2Nix {inherit pkgs;}) mkPoetryApplication;
    in rec {
      default = rico-hdl;

      # Wrapping idea from:
      # https://discourse.nixos.org/t/adding-non-python-dependencies-to-poetry2nix-application/26755/6
      rico-hdl = mkPoetryApplication {
        projectDir = ./.;
        preferWheels = true;
        nativeBuildInputs = [pkgs.makeBinaryWrapper];
        # maybe it is possible to rename the wrapper so that the
        # wrapped binary doesn't have an ugly name?
        propogatedBuildInputs = [pkgs.fd];
        postInstall = ''
          wrapProgram "$out/bin/rico-hdl" \
            --prefix PATH : ${pkgs.lib.makeBinPath [pkgs.fd]}
        '';
        meta.mainProgram = "rico-hdl";
        # Python312 breaks LMDB...
        # python = pkgs.python312;
        # no idea how to write this:
        # overrides = poetry2nix.overrides.withDefaults (final: prev: {
        #   lmdb = prev.lmdb.overridePythonAttrs (old: {
        #     LMDB_FORCE_SYSTEM=1;
        #   });
        # })
        # nativeBuildInputs = [pkgs.lmdb];
      };

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
          export RICO_HDL_S1_PATH=${./integration_tests/tiffs/BigEarthNet/BigEarthNet-S1}
          export RICO_HDL_S2_PATH=${./integration_tests/tiffs/BigEarthNet/BigEarthNet-S2}
          export RICO_HDL_HYSPECNET_PATH=${./integration_tests/tiffs/HySpecNet-11k}
          export RICO_HDL_LMDB_REF_PATH=${./integration_tests/BigEarthNet_LMDB}
          export RICO_HDL_UC_MERCED_PATH=${./integration_tests/UCMerced_LandUse}
          export RICO_HDL_EUROSAT_MS_PATH=${./integration_tests/tiffs/EuroSAT_MS}
          echo "Running Python integration tests."
          pytest ${./integration_tests/test_python_integration.py} && echo "Success!"
        '';
      };
    });

    devShells = eachSystem (system: let
      pkgs = pkgsFor.${system};
      lib = pkgs.lib;
      inherit (inputs.poetry2nix.lib.mkPoetry2Nix {inherit pkgs;}) mkPoetryEnv;
    in {
      default = inputs.devenv.lib.mkShell {
        inherit pkgs inputs;
        modules = [
          ({
            pkgs,
            config,
            ...
          }: {
            enterShell = self.checks.${system}.pre-commit-check.shellHook;
            env.RICO_HDL_HYSPECNET_PATH = "${config.env.DEVENV_ROOT}/integration_tests/tiffs/HySpecNet-11k/";
            env.RICO_HDL_UC_MERCED_PATH = "${config.env.DEVENV_ROOT}/integration_tests/tiffs/UCMerced_LandUse/";
            env.RICO_HDL_EUROSAT_MS_PATH = "${config.env.DEVENV_ROOT}/integration_tests/tiffs/EuroSAT_MS";
            env.RICO_HDL_S1_PATH = "${config.env.DEVENV_ROOT}/integration_tests/tiffs/BigEarthNet/BigEarthNet-S1";
            env.RICO_HDL_LMDB_REF_DATA_PATH = "${config.env.DEVENV_ROOT}/integration_tests/BigEarthNet_LMDB";
            env.RICO_HDL_S2_PATH = "${config.env.DEVENV_ROOT}/integration_tests/tiffs/BigEarthNet/BigEarthNet-S2";
            env.RICO_HDL_LMDB_REF_PATH = "${config.env.DEVENV_ROOT}/integration_tests/BigEarthNet_LMDB";
            env.JUPYTER_PATH = "${pkgs.python3Packages.jupyterlab}/share/jupyter";
            packages =
              [
                (mkPoetryEnv
                  {
                    projectDir = ./.;
                    preferWheels = true;
                    editablePackageSources = {
                      rico-hdl = ./src;
                    };
                  })
                pkgs.poetry
                pkgs.quarto
              ]
              ++ self.checks.${system}.pre-commit-check.enabledPackages;
          })
        ];
      };
    });
  };
}
