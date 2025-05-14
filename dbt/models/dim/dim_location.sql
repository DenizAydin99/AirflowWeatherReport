{{ config(
    materialized='incremental',
    unique_key='location_key',
    tags=['dim']
) }}

with src as (
    select distinct
        location_key,
        country,
        city_name,
        latitude,
        longitude
    from {{ ref('stg_weather_raw') }}
)

select * from src

{% if is_incremental() %}
where location_key not in (select location_key from {{ this }})
{% endif %}