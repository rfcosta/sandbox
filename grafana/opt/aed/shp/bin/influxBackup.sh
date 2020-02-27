#!/usr/bin/env bash

[[ $(whoami) == "centos" ]] || { sudo su - centos -c "$0 $*";exit; }

[ -f /etc/profile.d/shp_env.sh ] && source /etc/profile.d/shp_env.sh

DATABASE=kpi
BKPDIR=/mnt/backup
NOW=$(date -u +"%Y%m%dT%H%M%SZ")
BKPBASE=$BKPDIR/backups
TARBASE=$BKPDIR/tar/now
S3BASE="influx-backup"
S3DIR="$S3BASE-now"
S3URL=${AWS_BACKUP_BUCKET}/backups
BKPNOWDIR=$BKPBASE/$DATABASE/now
TARFILE=$DATABASE.$NOW.tar

if [ ! -d $BKPDIR ] ; then
    echo "$BKPDIR not found or not mounted!. Aborted"
    exit 8
fi

[ ! -d $BKPBASE ] && mkdir -p $BKPBASE
[ ! -d $TARBASE ] && mkdir -p $TARBASE
[ ! -d $BKPNOWDIR ] && mkdir -p $BKPNOWDIR

unset http_proxy
unset HTTP_PROXY
unset https_proxy
unset HTTPS_PROXY

influxd-ctl backup -full -db $DATABASE $BKPNOWDIR
tar -cvf $TARBASE/$TARFILE $BKPNOWDIR
aws s3 sync $TARBASE/ s3://$S3URL/$S3DIR/
rm -rf $BKPNOWDIR
rm -rf $TARBASE

echo " "
echo "Restore KPI no merge, empty DB: "
echo "Command: /opt/aed/shp/bin/influxRestore.sh $S3URL/$S3DIR/$TARFILE"
echo " "
