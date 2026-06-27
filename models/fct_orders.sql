-- Order fact. Grain: one row per order (order_key).
-- Line measures roll up from the order-item fact for reconciliation.

with orders as (
    select * from {{ ref('stg_orders') }}
),

item_rollup as (
    select
        order_key,
        count(*)            as item_count,
        sum(sale_price)     as total_revenue
    from {{ ref('stg_order_items') }}
    group by order_key
)

select
    o.order_key,
    o.customer_key,
    o.order_date,
    o.order_status,
    r.item_count,
    r.total_revenue
from orders o
left join item_rollup r on o.order_key = r.order_key
