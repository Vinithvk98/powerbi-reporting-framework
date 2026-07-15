-- Reporting views consumed by Power BI.
-- Keeping business logic in SQL views (rather than only in DAX) means the
-- same definitions are reusable across Power BI, ad-hoc SQL and tests.

-- Daily net spend by region and merchant category.
CREATE VIEW IF NOT EXISTS vw_daily_spend AS
SELECT d.date,
       d.year,
       d.month,
       a.region,
       m.category,
       COUNT(*)                        AS txn_count,
       SUM(f.signed_amount)            AS net_amount,
       SUM(CASE WHEN f.is_refund THEN f.amount ELSE 0 END) AS refund_amount
FROM fact_transaction f
JOIN dim_date     d ON f.date_key    = d.date_key
JOIN dim_account  a ON f.account_key = a.account_key
JOIN dim_merchant m ON f.merchant_key = m.merchant_key
GROUP BY d.date, d.year, d.month, a.region, m.category;

-- Monthly KPI feed for the executive summary page.
CREATE VIEW IF NOT EXISTS vw_monthly_kpi AS
SELECT d.year,
       d.month,
       d.month_name,
       COUNT(*)                                   AS txn_count,
       SUM(f.signed_amount)                       AS net_revenue,
       AVG(f.amount)                              AS avg_ticket,
       SUM(CASE WHEN f.is_refund THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS refund_rate
FROM fact_transaction f
JOIN dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month, d.month_name;

-- Data-quality exception feed for the "Data Quality" report page.
CREATE VIEW IF NOT EXISTS vw_dq_exceptions AS
SELECT rule, severity, COUNT(*) AS exception_count
FROM dq_exceptions
GROUP BY rule, severity;
