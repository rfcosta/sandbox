#!/usr/bin/env bash

DATABASE=kpi

echo "ALTER RETENTION POLICY on Database ${DATABASE}"
influx -execute "ALTER RETENTION POLICY days ON kpi DURATION 32d REPLICATION 2"
influx -execute "ALTER RETENTION POLICY months ON kpi DURATION 52w REPLICATION 2"
influx -execute "ALTER RETENTION POLICY years ON kpi DURATION 520w REPLICATION 2"

echo "CREATE CONTINUOUS QUERY on Database ${DATABASE}"
influx -execute "CREATE CONTINUOUS QUERY \"kpi_metric_cq_months\" ON \"kpi\" BEGIN SELECT mean(avg_processing_time) AS avg_processing_time, mean(error_count) AS error_count, mean(error_rate) AS error_rate, mean(transaction_count) AS transaction_count, mean(count) AS count, mean(currency) AS currency, mean(percent) AS percent, mean(threshold_dynamic_lower) AS threshold_dynamic_lower, mean(threshold_dynamic_upper) AS threshold_dynamic_upper, mean(threshold_static_lower) AS threshold_static_lower, mean(threshold_static_upper) AS threshold_static_upper INTO \"kpi\".\"months\".\"metric\" FROM \"kpi\".\"days\".\"metric\" WHERE time > now() - 1h GROUP BY time(5m), * END"
influx -execute "CREATE CONTINUOUS QUERY \"kpi_metric_cq_years\" ON \"kpi\" BEGIN SELECT mean(avg_processing_time) AS avg_processing_time, mean(error_count) AS error_count, mean(error_rate) AS error_rate, mean(transaction_count) AS transaction_count, mean(count) AS count, mean(currency) AS currency, mean(percent) AS percent, mean(threshold_dynamic_lower) AS threshold_dynamic_lower, mean(threshold_dynamic_upper) AS threshold_dynamic_upper, mean(threshold_static_lower) AS threshold_static_lower, mean(threshold_static_upper) AS threshold_static_upper INTO \"kpi\".\"years\".\"metric\" FROM \"kpi\".\"days\".\"metric\" WHERE time > now() - 1h GROUP BY time(15m), * END"

echo " "
echo "Done."
