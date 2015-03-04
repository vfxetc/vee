
# By sourcing this script, your vee commands with operate within a "demo"
# directory of the VEE source.


root="$(cd "$(dirname "${BASH_SOURCE[0]}")"; cd ..; pwd)"

# Clear out any existing variables.
unset VEE_DEV
unset VEE_REPO

# Setup demo VEE.
export VEE="$root/demo"
mkdir -p $VEE

# Use the test's sandbox
export VEE_HOMEBREW="$root/tests/sandbox/Homebrew"

# Use scripts from source.
export PATH="$root/bin:$PATH"
export PYTHONPATH="$root"


# Remove WX environ.
unset KS_SITES
unset KS_TOOLS

# Cleanup.
unset root
