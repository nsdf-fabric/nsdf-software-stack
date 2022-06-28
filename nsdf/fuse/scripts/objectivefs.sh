#!/bin/bash


# //////////////////////////////////////////////////////////////////////////
function Install_objectivefs() {

	wget -q https://objectivefs.com/user/download/asn7gu3nd/objectivefs_6.9.1_amd64.deb
	sudo dpkg -i objectivefs_6.9.1_amd64.deb
	rm objectivefs_6.9.1_amd64.deb

	sudo mkdir -p /etc/objectivefs.env
	sudo rm -Rf /etc/objectivefs.env/*
	sudo bash -c "echo ${AWS_ACCESS_KEY_ID}      > /etc/objectivefs.env/AWS_ACCESS_KEY_ID"
	sudo bash -c "echo ${AWS_SECRET_ACCESS_KEY}  > /etc/objectivefs.env/AWS_SECRET_ACCESS_KEY"
	sudo bash -c "echo ${AWS_DEFAULT_REGION}     > /etc/objectivefs.env/AWS_DEFAULT_REGION"
	sudo bash -c "echo ${OBJECTIVEFS_LICENSE}    > /etc/objectivefs.env/OBJECTIVEFS_LICENSE"
	sudo bash -c "echo ${OBJECTIVEFS_LICENSE}    > /etc/objectivefs.env/OBJECTIVEFS_PASSPHRASE"
	sudo chmod 600 /etc/objectivefs.env/*

	# check the version
	mount.objectivefs help 2>&1 | grep -i "Welcome to ObjectiveFS"
}

# //////////////////////////////////////////////////////////////////////////
function Uninstall_objectivefs() {
	sudo rm -f /etc/objectivefs.env/AWS_ACCESS_KEY_ID
	sudo rm -f /etc/objectivefs.env/AWS_SECRET_ACCESS_KEY
	sudo rm -f /etc/objectivefs.env/AWS_DEFAULT_REGION
	sudo rm -f /etc/objectivefs.env/OBJECTIVEFS_LICENSE
	sudo rm -f /etc/objectivefs.env/OBJECTIVEFS_PASSPHRASE
}

# //////////////////////////////////////////////////////////////////
# see https://objectivefs.com/howto/performance-amazon-efs-vs-objectivefs-large-files
function CreateBucket() {

    echo "CreateBucket  objectivefs..."

    # objectivefs does not seem to support https (!)
    __endpoint__=${AWS_S3_ENDPOINT_URL//https/http}/${BUCKET_NAME}


    cat << EOF > create_bucket.sh
#!/usr/bin/expect -f
set timeout -1
spawn mount.objectivefs create ${__endpoint__}
match_max 100000
expect -exact "Verify passphrase"
send -- "${OBJECTIVEFS_LICENSE}\r"
expect eof
EOF
    chmod a+x create_bucket.sh
    sudo ./create_bucket.sh
    rm create_bucket.sh

    # problem of file owned by root, remove it
    FuseUp
    Retry sudo rm -f ${TEST_DIR}/README
    FuseDown

    echo "CreateBucket  objectivefs done"
}



# //////////////////////////////////////////////////////////////////
function FuseUp() {

    echo "FuseUp objectivefs..."
    sync && DropCache
    mkdir -p ${TEST_DIR}
    
    # objectivefs does not seem to support https (!)
    __endpoint__=${AWS_S3_ENDPOINT_URL//https/http}/${BUCKET_NAME}

    export  DISKCACHE_PATH=${CACHE_DIR}

	# see https://objectivefs.com/userguide#disk-cache
	# The disk cache uses DISKCACHE_SIZE and DISKCACHE_PATH environment variables 
	# To enable disk cache, set DISKCACHE_SIZE
	# NOTE: here I am not enabling DISKCACHE_SIZE (!)

    sudo mount.objectivefs \
        -o mt \
        ${__endpoint__} \
        ${TEST_DIR}
    CheckMount ${TEST_DIR}
    sudo chmod a+rwX -R ${TEST_DIR}
    echo "FuseUp objectivefs done"
}

# //////////////////////////////////////////////////////////////////
function FuseDown() {
    # overrideing because I need sudo here
    echo "FuseDown objectivefs..."
    sync && DropCache
    Retry sudo umount ${TEST_DIR} 
    Retry sudo rm -Rf ${CACHE_DIR} 
    Retry sudo rm -Rf ${BASE_DIR}
    echo "FuseDown objectivefs done"
}