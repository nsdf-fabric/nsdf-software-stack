#!/bin/bash

# //////////////////////////////////////////////////////////////////////////
function Install_juicefs() {
	wget -q https://juicefs.com/static/juicefs
	sudo mv juicefs /usr/bin
	chmod +x /usr/bin/juicefs
	# check the version
	juicefs version	
}

# //////////////////////////////////////////////////////////////////////////
function Uninstall_juicefs() {
	sudo rm -f /usr/bin/juicefs
}

# //////////////////////////////////////////////////////////////////
function FuseUp() {
    echo "FuseUp juicefs ..."
    sync && DropCache
    mkdir -p ${TEST_DIR}

	# first authenticate
    # NOTE: the endpoint and the region are configured MANUALLY from the JuiceFS data portal
	juicefs auth ${BUCKET_NAME} \
		--token ${JUICE_TOKEN} \
		--accesskey ${AWS_ACCESS_KEY_ID} \
		--secretkey ${AWS_SECRET_ACCESS_KEY}  

    juicefs mount \
        ${BUCKET_NAME} \
        ${TEST_DIR} \
        --cache-dir=${CACHE_DIR} \
        --log=${LOG_DIR}/log.log \
        --max-uploads=150 
    CheckMount ${TEST_DIR}
    echo "FuseUp juicefs done"
}

# //////////////////////////////////////////////////////////////////
function FuseDown() {
    echo "FuseDown juicefs..."
    sync && DropCache
    Retry umount ${TEST_DIR}
    Retry rm -Rf ${CACHE_DIR} 
    Retry rm -Rf ${BASE_DIR}
    echo "FuseDown juicefs done"
}