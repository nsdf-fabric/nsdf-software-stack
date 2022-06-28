#!/bin/bash

# https://www.rath.org/s3ql-docs/man/mkfs.html
# https://www.rath.org/s3ql-docs/man/mount.html

# //////////////////////////////////////////////////////////////////////////
function Install_s3ql() {

	echo "NOTE fuse3 is not compatible with fuse, used by most of other software, so you will need to run this s3ql at the end**:"
	echo "After the test repristinate the normal fuse:"
	echo "  sudo apt remove  -y fuse3"
	echo "  sudo apt install -y fuse"

	sudo apt remove  -y fuse 
	sudo apt install -y sqlite3 libsqlite3-dev pkg-config libfuse3-dev fuse3

	sudo pip3 install --upgrade pip
	sudo pip3 install --upgrade pyfuse3 google-auth-oauthlib dugong apsw defusedxml trio

	wget https://github.com/s3ql/s3ql/releases/download/release-3.8.1/s3ql-3.8.1.tar.gz

	tar xzf s3ql-3.8.1.tar.gz
	pushd s3ql-3.8.1
	python3 setup.py build_ext --inplace
	sudo python3 setup.py install 
	popd
	sudo rm -Rf s3ql-3.8.1.tar.gz s3ql-3.8.1

	# check the version
	mount.s3ql --version	
}

# //////////////////////////////////////////////////////////////////////////
function Uninstall_s3ql() {
	sudo apt remove  -y fuse3
	sudo apt install -y fuse
	rm -f ~/.s3ql/authinfo2
}

# //////////////////////////////////////////////////////////////////
function CreateBucket() {

    echo "CreateBucket s3ql..."
	BaseCreateBucket ${BUCKET_NAME}

	
	#  example: s3c://s3.us-west-1.wasabisys.com:443/${BUCKET_NAME} 


	# start must be s3c (i.e. s3 compatible)
	# rath.org/s3ql-ocs/backends.html
	# NOTE: not sure if I need to add the 443 port
	__endpoint__=${AWS_S3_ENDPOINT_URL//https/s3c}/${BUCKET_NAME}
	
	# credentials
	mkdir -p ${HOME}/.s3ql/
	cat << EOF > $HOME/.s3ql/authinfo2
[nsdf-test]
storage-url: ${__endpoint__}
backend-login: ${AWS_ACCESS_KEY_ID}
backend-password: ${AWS_SECRET_ACCESS_KEY}
EOF
	chmod 600 ~/.s3ql/authinfo2


	# mount
    mkfs.s3ql  \
	    --authfile $HOME/.s3ql/authinfo2 \
        --cachedir ${CACHE_DIR} \
        --log ${LOG_DIR}/log \
        --plain \
        ${__endpoint__}
    echo "CreateBucket s3ql done"
}

# //////////////////////////////////////////////////////////////////
function FuseUp() {
    echo "FuseUp s3ql..."
    sync && DropCache
    mkdir -p ${TEST_DIR}

	__endpoint__=${AWS_S3_ENDPOINT_URL//https/s3c}/${BUCKET_NAME}

	 # --cachesize <size> Cache size in KiB (default: autodetect).
	 # here I am setting to 64MiB to keep it minimal
    Retry mount.s3ql \
	        --authfile $HOME/.s3ql/authinfo2 \
            --cachedir ${CACHE_DIR} \
            --log ${LOG_DIR}/log \
            --cachesize $(( 64 * 1024 )) \
            ${__endpoint__} \
            ${TEST_DIR} 
    
    CheckMount ${TEST_DIR}
    echo "FuseUp s3ql done"
}

# //////////////////////////////////////////////////////////////////
function FuseDown() {
    echo "FuseDown s3ql..."
    sync && DropCache
    Retry umount.s3ql --log ${LOG_DIR}/log ${TEST_DIR}
    Retry rm -Rf ${CACHE_DIR} 
    Retry rm -Rf ${BASE_DIR}
    echo "FuseDown s3ql done"
}
