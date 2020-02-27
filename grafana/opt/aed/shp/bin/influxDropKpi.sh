#!/usr/bin/env bash

DATABASE=kpi

echo "DROP DATABASE ${DATABASE}"
influx -execute "DROP DATABASE ${DATABASE}"

echo " "
echo "Done."
