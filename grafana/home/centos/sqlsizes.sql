SELECT table_name AS "Table"
, round(((data_length + index_length) / 1024 / 1024), 2) as size 
FROM information_schema.TABLES 
WHERE table_schema = "grafana" 
ORDER BY size DESC;

