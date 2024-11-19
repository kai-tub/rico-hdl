{
  lib,
  inputs,
}:
let
  cargo_toml = builtins.fromTOML (builtins.readFile ../Cargo.toml);
  mkDate =
    longDate:
    (lib.concatStringsSep "-" [
      (builtins.substring 0 4 longDate)
      (builtins.substring 4 2 longDate)
      (builtins.substring 6 2 longDate)
    ]);
in
{
  default =
    final: prev:
    let
      date = mkDate (inputs.self.lastModifiedDate or "19700101");
    in
    {
      rico-hdl = final.callPackage ./default.nix {
        version = "${cargo_toml.package.version}+date=${date}_${inputs.self.shortRev or "dirty"}";
        nix-filter = inputs.nix-filter.lib;
      };
    };
}
