# Architecture & Design Notes

## Why a star schema

Power BI performs best over a Kimball-style star: a narrow fact table joined
to a handful of conformed dimensions by integer surrogate keys. This design
keeps relationships single-direction and one-to-many, which makes DAX simpler
and the VertiPaq engine's compression and query plans efficient. A single flat
table would model fine for small data but degrades quickly and makes reusable
slicing (by region, category, time) awkward.

## The date dimension earns its keep

`dim_date` is generated to span the full range of the fact and is marked as the
model's date table. That one step unlocks Power BI time-intelligence —
`TOTALYTD`, `SAMEPERIODLASTYEAR`, `DATEADD` — so measures like `Net Revenue YTD`
and `Net Revenue MoM %` are one line each instead of hand-rolled date maths.

## Logic in views, not just DAX

Business definitions (daily net spend, monthly KPIs, exception rollups) live in
SQL views. Keeping them there means the same definition is consumed by Power BI,
by ad-hoc SQL, and by tests — a single source of truth. DAX measures then layer
interactive aggregation on top rather than re-deriving the base logic.

## Validation as a first-class stage

The reporting pipeline is `build model → validate → refresh`, not just
`build model → refresh`. Validation runs on every rebuild and writes every
offending row to `dq_exceptions` with a rule name and severity. Because the
exceptions are a table, they are charted on the dashboard next to the KPIs they
affect — so a stakeholder sees both the number and how much to trust it. This is
the difference between a dashboard that looks accurate and one that is
demonstrably accurate.

## Refresh orchestration

`etl.run` is the unit a scheduler drives (cron, Airflow, Azure Data Factory).
The recommended cadence is: nightly `etl.run` to rebuild + validate, then a
Power BI Service **scheduled refresh** immediately after. If validation returns
`passed: false` above an agreed threshold, the same summary can gate the refresh
or fire an alert.

## Scaling to a real warehouse

Everything is DSN-driven. Set `BI_WAREHOUSE_DSN` to a PostgreSQL or Azure SQL
connection and the identical ETL builds the production model; apply
`sql/star_schema.sql` and `sql/analytics_views.sql` there, and Power BI connects
by Import or DirectQuery. SQLite is only the zero-setup default for the demo.
