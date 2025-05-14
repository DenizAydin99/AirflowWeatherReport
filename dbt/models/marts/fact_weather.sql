{{ config(
    materialized='table',
    tags=['fact']
) }}

with base as (
    select
        -- foreign‑key look‑ups
        l.location_key,
        t.time_key,
        c.condition_key,

        -- measures
        f.temp,
        f.feels_like,
        f.temp_min,
        f.temp_max,
        f.pressure,
        f.humidity,
        f.wind_speed,
        f.wind_deg,
        f.wind_gust,
        f.cloudiness,
        f.visibility,
        f.sunrise,
        f.sunset
    from {{ ref('stg_weather_raw') }} as f

    left join {{ ref('dim_location') }} as l
        on l.location_key = f.location_key

    left join {{ ref('dim_condition') }} as c
        on c.condition_key = f.condition_key

    left join {{ ref('dim_time') }} as t
        on t.time_key = f.time_key
)

select *
from base

