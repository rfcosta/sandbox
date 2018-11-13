SELECT t.id,
       t.epoch,
       t.created,
       t.updated,
       t.org_id,
       t.dashboard_id,
       t.panel_id,
       t.region_id,
       t.title,
       t.text,
       t.tags

FROM annotation t
     ORDER BY created DESC
     LIMIT 501
