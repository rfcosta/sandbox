#!/bin/sh

# restoreTAR.sh <tar file with name like <database>.<retention period>.<timestamp>.tar

[ -f /etc/profile.d/shp_env.sh ] && source /etc/profile.d/shp_env.sh

S3TAR=$1

T1=${S3TAR#*.}
DATABASE=${S3TAR%%.*}
T2=${T1#*.}
RETENTION=${T1%%.*}
DAY=${T2%T*}
TIMESTAMP=${T2%.*}

# Example of restore (DATABASE=kpi, RETENTION=months, DAY=20180830):
# influxd-ctl restore -db kpi -rp months -newdb regi_kpi_months_20180830 /mnt/backup/restore/mnt/backup/backups/kpi/months/20180830
#   Using backup directory: /mnt/backup/restore/mnt/backup/backups/kpi/months/20180830
#   Using meta backup: 20180830T190017Z.meta
#   Restoring meta data... Done. Restored in 12.021989ms, 1 shards mapped
#   Restoring db kpi, rp months, shard 3 to shard 149...
#   Copying data to 10.123.209.157:8088... Copying data to 10.123.210.193:8088... Done. Restored shard 3 into shard 149 in 67.637101ms, 944128 bytes transferred
#   Restored from /mnt/backup/restore/mnt/backup/backups/kpi/months/20180830 in 79.721809ms, transferred 944128 bytes

# Example of MERGE
# [centos@teo002lisdid0rc ~]$ influx
#   Connected to http://localhost:8086 version 1.6.2-c1.6.2
#   InfluxDB shell version: unknown
# > settings
#   Setting           Value
#   --------          --------
#   Host              localhost:8086
#   Username
#   Database
#   RetentionPolicy
#   Pretty            false
#   Format            column
#   Write Consistency all
#   Chunked           true
#   Chunk Size        0
#
#  > show databases
#   name: databases
#   name
#   ----
#   kpi
#   non_kpi
#   _kapacitor
#   _internal
#   restored_kpi_days
#   restored_kpi_months
#   restored_kpi_years
#   regi_kpi_months_20180830

# -NOTE- retention policy goes on USE statement as well after database name
# -NOTE- select statement also includes retention period after database name

#  > use regi_kpi_months_20180830.months
#   Using database regi_kpi_months_20180830
#   Using retention policy months
#  > SELECT * INTO kpi.months.:MEASUREMENT FROM /.*/ GROUP BY *
#   name: result
#   time written
#   ---- -------
#   0    58693
#  >




# Check if database and retention policy are valid

DBOK=$(
    influxd-ctl show-shards | /usr/bin/awk 'NR > 3 {print $2, $3}' | /usr/bin/sort | /usr/bin/uniq | while read -r
    do
        read -r DATABASE_ITEM RETENTION_ITEM <<< "$REPLY"
        if [[ "$DATABASE" = "$DATABASE_ITEM" ]] && [[ "$RETENTION" = "$RETENTION_ITEM" ]] ; then
            echo 'OK'
        fi
    done
)

if [ "$DBOK" = 'OK' ] ; then
    echo "# $DATABASE / $RETENTION_POLICY OK "
else
    echo "# **ERROR** No shards found for $DATABASE / $RETENTION_POLICY "
    exit 16
fi



echo "# Database: $DATABASE  Retention: $RETENTION Day: $DAY"
S3URL=$AWS_DATA_BUCKET/backups
S3DIR="influx-backup-$DAY"
echo " aws s3 cp  s3://$S3URL/$S3DIR/$S3TAR $S3TAR "
sourceDIR=$PWD
echo "cd /"
echo "tar -xvf $sourceDIR/$S3TAR "
echo "cd $sourceDIR"
# Example: /mnt/backup/backups/kpi/days/20180531/
echo "unset https_proxy"
echo "unset http_proxy"
echo "influxd-ctl restore -db $DATABASE -rp $RETENTION -newdb restored_${DATABASE}_${RETENTION}_$TIMESTAMP /mnt/backup/backups/$DATABASE/$RETENTION/$DAY "

echo "# Commands to merge the data into database to be executed on any data node:"
echo "# (Copy and paste these commands to a data node, removing pound sign before you execute them)"
echo "# unset https_proxy"
echo "# unset http_proxy"
echo "# influx"
echo "# USE restored_${DATABASE}_${TIMESTAMP}.${RETENTION} "
echo '# SELECT * INTO ' ${DATABASE}'.'${RETENTION}'.:MEASUREMENT FROM /.*/ GROUP BY *'
echo "# "



