{{ config(
    materialized='incremental',
    unique_key='condition_key',
    tags=['dim']
) }}

with src as (
    select distinct
        condition_key,
        weather_main,
        weather_description
    from {{ ref('stg_weather_raw') }}
)

select * from src

{% if is_incremental() %}
where condition_key not in (select condition_key from {{ this }})
{% endif %}