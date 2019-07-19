#!/usr/bin/env bash

# Variables that will be available

#AWS_STACK=shpInfluxCluster2
#AWS_BUCKET=s3-dev-us-west-2-shp-data
#AWS_REGION=us-west-2
#BKPDIR=/mnt/backup


set -x

DATABASE=${1:-kpi}
RETENTION_POLICY=${2:-days}
BACKUP=${3:-YES}

# Check if database and retention policy are valid

DBOK=$(
    influxd-ctl show-shards | /usr/bin/awk 'NR > 3 {print $2, $3}' | /usr/bin/sort | /usr/bin/uniq | while read -r
    do
        read -r DATABASE_ITEM RETENTION_ITEM <<< "$REPLY"
        if [[ "$DATABASE" = "$DATABASE_ITEM" ]] && [[ "$RETENTION_POLICY" = "$RETENTION_ITEM" ]] ; then
            echo 'OK'
        fi
    done
)

if [ "$DBOK" = 'OK' ] ; then
    echo "$DATABASE / $RETENTION_POLICY OK "
else
    echo "**ERROR** No shards found for $DATABASE / $RETENTION_POLICY "
    exit 16
fi



[ -f /etc/profile.d/shp_env.sh ] && source /etc/profile.d/shp_env.sh
# AWS_BACKUP_BUCKET=${AWS_BUCKET%-*}-data   # Special bucket for backup

# Get UTC timestamps
NOW=$(date -u +"%Y%m%dT%H%M%SZ")  # Right now
HOUR=$(date -u +"%Y%m%dT%H")      # Hour
TDY=$(date -u +"%Y%m%d")          # Today

RANDOMWAIT=$(expr $RANDOM % 60 + 1)

sleep $RANDOMWAIT

if [ "X$BKPDIR" = "X" ] ; then
    BKPDIR=/mnt/backup
fi

if [ ! -d $BKPDIR ] ; then
    echo "$BKPDIR not found or not mounted!. Aborted"
    exit 8
fi

BKPBASE=$BKPDIR/backups
TARBASE=$BKPDIR/tar/$TDY
S3BASE="influx-backup"
S3DIR="$S3BASE-$TDY"
# Example: S3URL=s3-dev-us-west-2-shp-data/backups
S3URL=${AWS_BACKUP_BUCKET}/backups





#BKPNOWDIR=$BKPBASE/$DATABASE/$RETENTION_POLICY/$NOW
BKPNOWDIR=$BKPBASE/$DATABASE/$RETENTION_POLICY/$TDY  # Make differential backups within the day

TARPREFIX=$DATABASE.$RETENTION_POLICY.$HOUR
TARFILE=$DATABASE.$RETENTION_POLICY.$NOW.tar   # was tar.gz

echo "Tar is $TARFILE on $TARBASE"
echo "Backup Directory is $BKPNOWDIR"


OUTTHERE=$(aws s3 ls s3://$S3URL/$S3DIR/$TARPREFIX)

if [ ! "X$OUTTHERE" = "X" ] ; then
    echo "$TARFILE Already there..: $OUTTHERE"
    exit
fi

[ ! -d $BKPBASE ] && mkdir -p $BKPBASE
[ ! -d $TARBASE ] && mkdir -p $TARBASE
[ ! -d $BKPNOWDIR ] && mkdir -p $BKPNOWDIR

unset http_proxy
unset https_proxy


if [ "$BACKUP" = "YES" ]  ; then
    #influxd-ctl  backup -full -db $DATABASE -rp $RETENTION_POLICY $BKPNOWDIR
    influxd-ctl  backup -db $DATABASE -rp $RETENTION_POLICY $BKPNOWDIR
    tar -cvf   $TARBASE/$TARFILE $BKPNOWDIR     # was -czvf
    aws s3 sync $TARBASE/ s3://$S3URL/$S3DIR/
    #rm -vr $BKPNOWDIR # Clean backup that as tar'ed
fi
set -

# backup additional parameteres that are not used.
         # -from <data-node-TCP-bind-address> \
         # -shard <shard-id> \

# Crontab to run this script:

# Minute   Hour   Day of Month       Month          Day of Week    Command
# (0-59)  (0-23)     (1-31)    (1-12 or Jan-Dec)  (0-6 or Sun-Sat)
#   0 * * * * /opt/aed/shp/bin/fullBackup.sh >> /tmp/fullBackup.`/usr/bin/date +\%Y\%m\%d`.txt 2>&1
#





