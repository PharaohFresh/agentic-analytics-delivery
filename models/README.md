# Models (illustrative)

Minimal dbt-style models showing the kind of artifact the delivery pattern
operates on. They mirror the structure of the companion warehouse repo
([`analytics-engineering-portfolio`](https://github.com/PharaohFresh/analytics-engineering-portfolio))
and exist here only to make the agents/runbooks concrete — this repo is the
*delivery model*, not a warehouse.

- `stg_orders.sql` — staging: 1:1 with source, renamed and typed.
- `fct_orders.sql` — order fact, grain stated explicitly (one row per order).
