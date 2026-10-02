{
  description = "Nix development environment for Anomaly Data Pipeline";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in {
          default = pkgs.mkShell {
            packages = [
              pkgs.gnumake
              pkgs.python313
              pkgs.uv
            ];

            UV_PYTHON = "${pkgs.python313}/bin/python3.13";
            UV_PROJECT_ENVIRONMENT = ".venv";
          };
        });
    };
}
