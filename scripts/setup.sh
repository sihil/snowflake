#!/usr/bin/env zsh

set -euo pipefail

# ensure we're in the root of the repo by getting the scripts directory and then moving up one level
pushd "$(dirname "${0}")/.."

# setup an exit hook to ensure we return to the original directory
trap 'popd' EXIT

pyenv rehash

python_version=$(cat .python-version-number)

pyenv install -s "${python_version}"

# check if a pyenv venv snowflake exists and if not create it
if ! pyenv versions | grep "snowflake"; then
    pyenv virtualenv "${python_version}" snowflake
fi

pip install -r requirements.txt