#!/usr/bin/bash

# installation script for litestar-pulse [https://github.com/trmznt/litestar-pulse]

# optional variable:
# - BASEDIR
# - OMIT

set -eu

# run the base.sh
# Detect the shell from which the script was called
parent=$(ps -o comm $PPID |tail -1)
parent=${parent#-}  # remove the leading dash that login shells have
case "$parent" in
  # shells supported by `micromamba shell init`
  bash|fish|xonsh|zsh)
    shell=$parent
    ;;
  *)
    # use the login shell (basename of $SHELL) as a fallback
    shell=${SHELL##*/}
    ;;
esac

# Parsing arguments
if [ -t 0 ] && [ -z "${BASEDIR:-}" ]; then
  printf "Base installation directory? [./cmsfix2] "
  read BASEDIR
fi

# default value
BASEDIR="${BASEDIR:-./cmsfix2}"

uMAMBA_ENVNAME="${uMAMBA_ENVNAME:-cmsfix2}"

mkdir -p ${BASEDIR}/instances/

# install litestar-pulse
source <(curl -L https://raw.githubusercontent.com/trmznt/litestar-pulse/main/install.sh)

echo "Cloning cmsfix2"
git clone --depth 1 https://github.com/trmznt/cmsfix2.git ${ENVS_DIR}/cmsfix2

# perform 2nd stage installation for CMSFix2
source ${ENVS_DIR}/cmsfix2/etc/inst-scripts/inst-stage-2.sh

# add to installed-repo.txt
echo "cmsfix2" >> ${ETC_DIR}/installed-repo.txt

echo
echo "CMSFix2 has been successfully installed. "
echo "Please read the docs for further setup."
echo "The base installation directory (VVG_BASEDIR) is:"
echo
echo `realpath ${BASEDIR}`
echo
echo "To activate the basic cmsfix2 environment (eg. for installing"
echo "or setting up base enviroment directory), execute the command:"
echo
echo `realpath ${BASEDIR}`/bin/activate
echo

# EOF