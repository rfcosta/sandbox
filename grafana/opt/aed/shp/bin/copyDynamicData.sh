#!/usr/bin/env bash

[[ $(whoami) == "centos" ]] || { sudo su - centos -c "$0 $*";exit; }

[ -f /etc/profile.d/shp_env.sh ] && source /etc/profile.d/shp_env.sh

if [ "$#" -ne 2 ]; then
    echo "Parameters incorrect, use: $0 <<Source>> <<Target>>"
    echo "Example: $0 ${AWS_DATA_BUCKET} ${AWS_DATA_BUCKET}"
    exit 2
fi

S3URL_SRC=${1}
S3URL_TARGET=${2}
BASE_DIR="/tmp/dynamic-thresholds"
THRESHOLDS_DIR="dynamic-thresholds/thresholds_history"
S3_SRC_URL=${S3URL_SRC}/${THRESHOLDS_DIR}
S3_TARGET_URL=${S3URL_TARGET}/${THRESHOLDS_DIR}

OUTTHERE=$(aws s3 ls s3://$S3URL_SRC)
if [ "X$OUTTHERE" = "X" ] ; then
    echo "s3://$S3URL_SRC not found!"
    exit
fi

OUTTHERE=$(aws s3 ls s3://$S3URL_TARGET)
if [ "X$OUTTHERE" = "X" ] ; then
    echo "s3://$S3URL_TARGET not found!"
    exit
fi

mkdir -p ${BASE_DIR}
mkdir -p /tmp/${THRESHOLDS_DIR}

aws s3 sync s3://${S3_SRC_URL} /tmp/${THRESHOLDS_DIR}
aws s3 sync /tmp/${THRESHOLDS_DIR} s3://${S3_TARGET_URL}

rm -rf ${BASE_DIR}
