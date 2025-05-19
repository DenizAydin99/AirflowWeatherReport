{{ config(
    materialized='incremental',
    unique_key='time_key',
    tags=['dim']
) }}

with src as (
    select distinct
        time_key,
        observation_hour,
        date_trunc('day', entry_date) as observation_date,
        extract(hour from entry_date) as observation_hour_number,
        extract(day from entry_date) as observation_day,
        extract(month from entry_date) as observation_month,
        cast(extract(year from entry_date) as int) as observation_year
    from {{ ref('stg_weather_raw') }}
)

select * from src

{% if is_incremental() %}
where time_key not in (select time_key from {{ this }})
{% endif %}
