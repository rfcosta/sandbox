select region_id
, id
, org_id
, dashboard_id
, panel_id
, type
, substr(text,117,126) as  'CHANGE'
from annotation
 where text like '%CHG%';
