#!/bin/sh
# ********************
#   INIT kpi database
# ********************

alias ifx='influx -host 127.0.0.1 -port 8086 -execute '
ifx "SHOW DATABASES"
ifx "CREATE DATABASE \"kpi\" WITH DURATION 32d REPLICATION 2 NAME \"days\""
ifx "SHOW DATABASES"
ifx "CREATE RETENTION POLICY \"months\" ON \"kpi\" DURATION 56w REPLICATION 2"
ifx "CREATE RETENTION POLICY \"years\" ON \"kpi\" DURATION 520w REPLICATION 2"

ifx "CREATE CONTINUOUS QUERY \"kpi_metric_cq_months\" ON \"kpi\" BEGIN SELECT mean(avg_processing_time) AS avg_processing_time, mean(error_count) AS error_count, mean(error_rate) AS error_rate, mean(transaction_count) AS transaction_count, mean(threshold_dynamic_lower) AS threshold_dynamic_lower, mean(threshold_dynamic_upper) AS threshold_dynamic_upper, mean(threshold_static_lower) AS threshold_static_lower, mean(threshold_static_upper) AS threshold_static_upper INTO \"kpi\".\"months\".\"metric\" FROM \"kpi\".\"days\".\"metric\" WHERE time > now() - 1h GROUP BY time(5m), * END"

ifx "CREATE CONTINUOUS QUERY \"kpi_threshold_cq_months\" ON \"kpi\" BEGIN SELECT mean(avg_processing_time_crit_lower) AS avg_processing_time_crit_lower, mean(avg_processing_time_crit_upper) AS avg_processing_time_crit_upper, mean(error_count_crit_lower) AS error_count_crit_lower, mean(error_count_crit_upper) AS error_count_crit_upper, mean(transaction_count_crit_lower) AS transaction_count_crit_lower, mean(transaction_count_crit_upper) AS transaction_count_crit_upper INTO \"kpi\".\"months\".\"thresholds\" FROM \"kpi\".\"days\".\"thresholds\" WHERE time > now() - 1h GROUP BY time(5m), * END"

ifx "CREATE CONTINUOUS QUERY \"kpi_metric_cq_years\" ON \"kpi\" BEGIN SELECT mean(avg_processing_time) AS avg_processing_time, mean(error_count) AS error_count, mean(error_rate) AS error_rate, mean(transaction_count) AS transaction_count, mean(threshold_dynamic_lower) AS threshold_dynamic_lower, mean(threshold_dynamic_upper) AS threshold_dynamic_upper, mean(threshold_static_lower) AS threshold_static_lower, mean(threshold_static_upper) AS threshold_static_upper INTO \"kpi\".\"years\".\"metric\" FROM \"kpi\".\"days\".\"metric\" WHERE time > now() - 1h GROUP BY time(15m), * END"

ifx "CREATE CONTINUOUS QUERY \"kpi_threshold_cq_years\" ON \"kpi\" BEGIN SELECT mean(avg_processing_time_crit_lower) AS avg_processing_time_crit_lower, mean(avg_processing_time_crit_upper) AS avg_processing_time_crit_upper, mean(error_count_crit_lower) AS error_count_crit_lower, mean(error_count_crit_upper) AS error_count_crit_upper, mean(transaction_count_crit_lower) AS transaction_count_crit_lower, mean(transaction_count_crit_upper) AS transaction_count_crit_upper INTO \"kpi\".\"years\".\"thresholds\" FROM \"kpi\".\"days\".\"thresholds\" WHERE time > now() - 1h GROUP BY time(5m), * END"

ifx "CREATE DATABASE \"non_kpi\" WITH DURATION 32d REPLICATION 1 NAME \"days\""
ifx "CREATE DATABASE \"_kapacitor\" WITH DURATION 32d REPLICATION 1 NAME \"monitor\""
ifx "SHOW DATABASES"


