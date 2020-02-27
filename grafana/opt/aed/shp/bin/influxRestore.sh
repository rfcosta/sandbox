#!/usr/bin/env bash

[[ $(whoami) == "centos" ]] || { sudo su - centos -c "$0 $*";exit; }

[ -f /etc/profile.d/shp_env.sh ] && source /etc/profile.d/shp_env.sh

DATABASE=kpi
S3URL=${1}
BKPDIR=/mnt/backup
BKPBASE=$BKPDIR/backups
RESTOREBASE=$BKPDIR/restore/now
S3FILE=$(basename $S3URL)

if [ ! -d $BKPDIR ] ; then
    echo "$BKPDIR not found or not mounted!. Aborted"
    exit 8
fi

OUTTHERE=$(aws s3 ls s3://$S3URL)
if [ "X$OUTTHERE" = "X" ] ; then
    echo "s3://$S3URL not found!"
    exit
fi

[ ! -d $BKPBASE ] && mkdir -p $BKPBASE
[ ! -d $RESTOREBASE ] && mkdir -p $RESTOREBASE

aws s3 cp s3://$S3URL $RESTOREBASE/
cd /
tar -xvf $RESTOREBASE/$S3FILE

unset http_proxy
unset HTTP_PROXY
unset https_proxy
unset HTTPS_PROXY

influxd-ctl restore -full $BKPBASE/$DATABASE/now/*.manifest

rm -rf $BKPDIR/restore
rm -rf $BKPBASE/$DATABASE/now
cd ~
