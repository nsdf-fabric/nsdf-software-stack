#!/bin/bash

# verbose
set -o verbose

#stop on error
set -e

export AWS_PROFILE=wasabi 
export S3_ENDPOINT=https://s3.us-west-1.wasabisys.com

# remote1 -> local1 -> local2 -> remote2
export REMOTE1=s3://exxon_pari_jan2013/idx
export LOCAL1=/tmp/buckets/exxon_pari_jan2013/idx
export LOCAL2=/tmp/buckets/exxon_pari_jan2013-time
export REMOTE2=${S3_ENDPOINT}/exxon_pari_jan2013-time

export SRC=${LOCAL1}/pari_full_semb3x3_trim.idx
export DST=${LOCAL2}/visus.idx

sudo mkdir -p       /tmp/buckets
sudo chmod a+rwX -R /tmp/buckets

# check the connection is working
s5cmd --endpoint-url ${S3_ENDPOINT} ls

# ////////////////////////////////////////////////////////////////////
function Convert {

  if [[ -f /tmp/done/${t} ]] ; then
     echo "# bash convert ${t} already exists, skipping"
  else

    echo "# bash convert ${t} begin..."

    # remote1 -> local1
    s5cmd --numworkers 48 --endpoint-url ${S3_ENDPOINT} sync --size-only ${REMOTE1}/* ${LOCAL1}/

    # create local2 idx
    python3 -c "from OpenVisus import CreateIdx,Field;CreateIdx(url='${DST}',dim=3,dims=[4301,3533,1501],fields=[Field('data','uint8','row_major')],time=[0,100,'time_%02d/'])"

    # local1->local2 (~20 minutes)
    echo "# bash python transform ${t} "
    time python3 ./transform.py --src ${SRC} --dst ${DST} --timestep ${t}  --shift "(0,${t},${t})" --slabs "(0,-1,64)"

    # local2->remote2 (~150 minutes)
    echo "# base python copy-blocks ${t} "
    time python3 ./s3.py copy-blocks --src ${DST} --dst ${REMOTE2} --timestep ${t}

    # remote local2 (~0 minutes)
    echo "# base rm -Rf ${t} "
    time rm -Rf ${LOCAL2}

    # keep track
    mkdir -p /tmp/done
    touch /tmp/done/${t}

    echo "# bash convert ${t} END"
  fi
}

# START=0 STEP=3 ./run.sh
for (( t=${START};  t < 100 ; t+=${STEP} )) ; do 
  Convert ${t} 
done



