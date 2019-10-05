#!/usr/bin/env bash

DATABASE=kpi
RESTORED_DB=restored_${DATABASE}_now

echo "Restore Database from ${RESTORED_DB} to ${DATABASE}"

influx -execute "ALTER RETENTION POLICY days ON ${DATABASE} DURATION 42d"
influx -execute "SELECT * INTO ${DATABASE}.days.:MEASUREMENT FROM ${RESTORED_DB}.days./.*/ GROUP BY *" -database="${RESTORED_DB}"
influx -execute "ALTER RETENTION POLICY days ON ${DATABASE} DURATION 32d"
influx -execute "ALTER RETENTION POLICY months ON ${DATABASE} DURATION 432d"
influx -execute "SELECT * INTO ${DATABASE}.months.:MEASUREMENT FROM ${RESTORED_DB}.months./.*/ GROUP BY *" -database="${RESTORED_DB}"
influx -execute "ALTER RETENTION POLICY months ON ${DATABASE} DURATION 392d"
influx -execute "SELECT * INTO ${DATABASE}.years.:MEASUREMENT FROM ${RESTORED_DB}.years./.*/ GROUP BY *" -database="${RESTORED_DB}"
influx -execute "DROP DATABASE ${RESTORED_DB}"

echo " "
echo "Done."
