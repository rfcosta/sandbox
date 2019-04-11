select id, org_id, dashboard_id, panel_id,type,region_id,substr(text,117,126) from annotation where text like '%CHG%';
