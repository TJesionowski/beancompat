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
            pkgs.cargo
            pkgs.rustc
          ];

          shellHook = ''
            export VIRTUAL_ENV="$PWD/.venv"
            if [ ! -d "$VIRTUAL_ENV" ]; then
              python -m venv "$VIRTUAL_ENV"
            fi
            export PATH="$VIRTUAL_ENV/bin:$PATH"

            # Separate venv for beancount v2 (used by beancountv2 adapter)
            export BEANCOUNT_V2_VENV="$PWD/.venv-beancount-v2"
            if [ ! -d "$BEANCOUNT_V2_VENV" ]; then
              python -m venv "$BEANCOUNT_V2_VENV"
              "$BEANCOUNT_V2_VENV/bin/pip" install -q beancount==2.3.6 beanquery
            fi
          '';
        };
      });
}
