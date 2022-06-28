#!/bin/bash


# //////////////////////////////////////////////////////////////////////////
function Install_goofys() {
	wget https://github.com/kahing/goofys/releases/latest/download/goofys
	sudo mv goofys /usr/bin/
	chmod a+x /usr/bin/goofys

	# check the version
	goofys --version	
}

# //////////////////////////////////////////////////////////////////////////
function Uninstall_goofys() {
	sudo rm -f /usr/bin/goofys
}

# //////////////////////////////////////////////////////////////////
function FuseUp() {
    echo "FuseUp goofys..."
    sync && DropCache
    mkdir -p ${TEST_DIR}
    # Goofys does not have an on disk data cache (checkout catfs)
	 # see also https://spell.ml/docs/resources/
    goofys \
	 	--region ${AWS_DEFAULT_REGION} \
		 --endpoint ${AWS_S3_ENDPOINT_URL} ${BUCKET_NAME} ${TEST_DIR}
    CheckMount ${TEST_DIR}
    echo "FuseUp goofys done"
}

# //////////////////////////////////////////////////////////////////
function FuseDown() {
    echo "FuseDown goofys..."
    sync && DropCache
    Retry umount ${TEST_DIR}
    Retry rm -Rf ${CACHE_DIR} 
    Retry rm -Rf ${BASE_DIR}
    echo "FuseDown goofys done"
}
