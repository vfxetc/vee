
./configure --prefix "$VEE_BUILD_PATH/build"
make
make install

export VEE_BUILD_SUBDIR_TO_INSTALL=build
