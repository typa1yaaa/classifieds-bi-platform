WITH toDate('{{ period.start }}') AS d1,
     toDate('{{ period.end }}') AS d2,
     d1 - (d2 - d1 + 1) AS p1,
     d1 - 1 AS p2
SELECT sumIf(views, event_date BETWEEN d1 AND d2) AS views_cur,
       sumIf(views, event_date BETWEEN p1 AND p2) AS views_prev,
       sumIf(contacts, event_date BETWEEN d1 AND d2) AS contacts_cur,
       sumIf(contacts, event_date BETWEEN p1 AND p2) AS contacts_prev,
       round(100 * contacts_cur / nullIf(views_cur, 0), 2) AS cr_cur_pct,
       round(100 * contacts_prev / nullIf(views_prev, 0), 2) AS cr_prev_pct
FROM marts.fct_category_daily
WHERE event_date BETWEEN p1 AND d2
  AND category_id IN ({{ category }})
  AND platform IN ({{ platform }})
