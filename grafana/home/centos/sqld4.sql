select dashboard_id, min(created) as "earliest"
, max(created) as "latest"
, substr(data, locate("uid",data)+6, 32) as "UID"
-- , substr(data, locate(',"title":"',data)+0, 32) as "TITLE"
, substr(data, locate(',"timezone":"',data)+31, 32) as "TITLE"
, count(*) as "Versions"
from dashboard_version
where dashboard_id = 1244
-- where substr(data, length(data)-45, 32) = "445796566f533140c423884f8e3ee41e"
group by dashboard_id, substr(data, locate("UID",data)+6, 32)
order by substr(data, locate("UID",data)+6, 32)
