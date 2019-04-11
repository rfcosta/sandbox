use grafana;

select dashboard_id
, count(*) as 'ROWS' 
, substr(FROM_UNIXTIME(min(created) /1000),3,14) as 'FROM'
, substr(FROM_UNIXTIME(max(created) /1000),3,14) as 'TO'  
from annotation 
group by dashboard_id 
order by `ROWS` desc
;
