
_vee_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"; cd ..; pwd)"

export VEE="$_vee_root/tests/sandbox/vee"
export PATH="$_vee_root/bin:$PATH"

unset _vee_root
unset PYTHONPATH
