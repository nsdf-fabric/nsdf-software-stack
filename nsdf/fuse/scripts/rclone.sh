#!/bin/bash


# //////////////////////////////////////////////////////////////////////////
function Install_rclone() {
	curl https://rclone.org/install.sh | sudo bash
	# check the version
	rclone --version	
}

# //////////////////////////////////////////////////////////////////////////
function Uninstall_rclone() {
	rm -f ~/.config/rclone/rclone.conf
}

# //////////////////////////////////////////////////////////////////
function FuseUp() {
    echo "FuseUp rclone..."
    sync && DropCache

    # authentication
	mkdir -p ~/.config/rclone/
	cat << EOF >> ~/.config/rclone/rclone.conf
[nsdf-test-rclone]
type=s3
provider=Other
access_key_id=${AWS_ACCESS_KEY_ID}
secret_access_key=${AWS_SECRET_ACCESS_KEY}
region=${AWS_DEFAULT_REGION} 
endpoint=${AWS_S3_ENDPOINT_URL}
EOF
	chmod 600 ~/.config/rclone/rclone.conf


	# NOTE: Without the use of --vfs-cache-mode this can only write files sequentially,  it can only seek when reading.
	# NOTE: I wasn't able to control the max cache size by  --vfs-cache-max-size so i lowered the total IO a activity
    mkdir -p ${TEST_DIR}
    #--vfs-cache-mode full \
    rclone mount \
        nsdf-test-rclone:${BUCKET_NAME} \
        ${TEST_DIR} \
		  --daemon \
        --cache-dir ${CACHE_DIR} 
    
    CheckMount ${TEST_DIR}
    echo "FuseUp rclone done"
}


# //////////////////////////////////////////////////////////////////
function FuseDown() {
    echo "FuseDown rclone..."
    sync && DropCache
    Retry umount ${TEST_DIR}
    Retry rm -Rf ${CACHE_DIR} 
    Retry rm -Rf ${BASE_DIR}
    echo "FuseDown rclone done"
}