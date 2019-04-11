use grafana;
select t.dashboard_id
,      count(*) as 'Versions'
from dashboard_version t
group by t.dashboard_id
order by Versions desc, t.dashboard_id
