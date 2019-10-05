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
unset https_proxy
influxd-ctl restore -db $DATABASE -newdb restored_${DATABASE}_now $BKPBASE/$DATABASE/now
rm -rf $BKPDIR/restore
rm -rf $BKPBASE/$DATABASE/now
cd ~

echo " "
echo "# Commands to merge the data into database to be executed on any data node:"
echo " influx"
echo " USE restored_${DATABASE}_now.days"
echo " ALTER RETENTION POLICY days ON kpi DURATION 42d"
echo " SELECT * INTO ${DATABASE}..:MEASUREMENT FROM /.*/ GROUP BY *"
echo " ALTER RETENTION POLICY days ON kpi DURATION 32d"
echo " USE restored_${DATABASE}_now.months"
echo " ALTER RETENTION POLICY days ON kpi DURATION 432d"
echo " SELECT * INTO ${DATABASE}..:MEASUREMENT FROM /.*/ GROUP BY *"
echo " ALTER RETENTION POLICY days ON kpi DURATION 392d"
echo " USE restored_${DATABASE}_now.years"
echo " SELECT * INTO ${DATABASE}..:MEASUREMENT FROM /.*/ GROUP BY *"
echo " DROP DATABASE restored_${DATABASE}_now"
echo " "
#echo "Execute on Restore Data node: "
#echo "Command: /opt/aed/shp/bin/restoreDb.sh"
#echo " "
