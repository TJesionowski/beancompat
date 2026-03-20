{
  description = "beancompat - black-box property tests for beancount implementations";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python312;
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            (python.withPackages (ps: with ps; [
              pip
              virtualenv
            ]))
          ];

          shellHook = ''
            export VIRTUAL_ENV="$PWD/.venv"
            if [ ! -d "$VIRTUAL_ENV" ]; then
              python -m venv "$VIRTUAL_ENV"
            fi
            export PATH="$VIRTUAL_ENV/bin:$PATH"
          '';
        };
      });
}
