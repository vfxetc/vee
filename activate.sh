
# This is for development!!

# It assumes the directory containing this repo is the VEE prefix, and
# creates/activates a venv there.

here="$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd)"

export VEE="$(dirname "$here")"

export VEE_VENV="$VEE/venv"
if [[ ! -f "$VEE_VENV/bin/activate" ]]; then
	python3 -m venv "$VEE_VENV"
fi
source "$VEE_VENV/bin/activate"

vee_cmd="$VEE_VENV/bin/vee"
if [[ ! -e "$vee_cmd" ]]; then
	pip install -e "$here"
fi
