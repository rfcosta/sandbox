use grafana;
set @c = 0;
select (@c:=@c+1) as 'Ordinal'
, region_id
, id
, org_id
, dashboard_id
, panel_id
, type
, epoch
, substr(FROM_UNIXTIME(epoch/1000),3,14) as Date
, substr(text,117,126) as  'Change'
from annotation
 where text like '%CHG%'
 order by id 
;
