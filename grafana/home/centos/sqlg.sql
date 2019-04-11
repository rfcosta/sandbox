use information_schema
SELECT TABLE_NAME, TABLE_ROWS, NOW() FROM `information_schema`.`tables` 
            WHERE `table_schema` = 'grafana'
              AND TABLE_ROWS > 0
;
