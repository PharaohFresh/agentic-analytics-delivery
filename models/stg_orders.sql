-- Staging: 1:1 with the orders source, renamed and typed. No business logic.

with source as (
    select * from {{ source('app', 'orders') }}
)

select
    order_id                    as order_key,
    customer_id                 as customer_key,
    status                      as order_status,
    created_at                  as order_created_at,
    cast(created_at as date)    as order_date
from source
