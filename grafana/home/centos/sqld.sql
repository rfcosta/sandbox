
use grafana;

select 
       min(created) as 'OLDEST'
,      max(created) as 'NEWEST'  
,      dashboard_id
,      count(*)     as 'ROWS' 
from dashboard_version 
group by
        dashboard_id
order by `ROWS` desc
;


