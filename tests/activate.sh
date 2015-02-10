
_tests="$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd)"
_root="$(dirname "$_tests")"
_sandbox="$_tests/sandbox"

export VEE_HOME="$_sandbox/home"
export VEE_REPO="$_sandbox/repo"


type vee 2>/dev/null
if [[ $? != 0 ]]; then
    alias vee='python -m vee'
fi
