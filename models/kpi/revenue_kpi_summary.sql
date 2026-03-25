{{ config(
    materialized='table',
    schema='dwh',
    tags=['kpi', 'revenue', 'rms-2001']
) }}

/*
  Model: revenue_kpi_summary
  Description: Aggregates monthly revenue by region and product line.
  Jira: RMS-2001
*/

WITH base_orders AS (
    SELECT
        o.region,
        o.product_line,
        o.currency_code,
        DATE_TRUNC('month', o.order_date) AS period_month,
        SUM(o.net_amount)                 AS revenue_amount
    FROM {{ ref('stg_orders') }} o
    WHERE o.status = 'COMPLETED'
    GROUP BY 1, 2, 3, 4
),

exchange_rates AS (
    SELECT
        currency_code,
        exchange_rate,
        rate_date
    FROM {{ ref('stg_exchange_rates') }}
    WHERE currency_code != 'BRL'
)

SELECT
    b.region,
    b.product_line,
    b.currency_code,
    b.period_month,
    ROUND(b.revenue_amount * COALESCE(er.exchange_rate, 1.0), 2) AS revenue_amount
FROM base_orders b
LEFT JOIN exchange_rates er
    ON er.currency_code = b.currency_code
    AND er.rate_date = b.period_month
