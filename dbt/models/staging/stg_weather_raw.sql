{{ config(
    materialized='table',
    tags=['stg']
) }}

with source as (

    select * 
    from {{ source('landing','weather_raw') }}

),

prepared as (

    select
        country,
        city_name,
        latitude,
        longitude,
        weather_main,
        weather_description,
        cast(temp            as float)  as temp,
        cast((temp * 9.0 / 5.0) + 32 as float)                               as temp_fahrenheit,
        cast(feels_like      as float)                                       as feels_like,
        cast(temp_min        as float)                                       as temp_min,
        cast(temp_max        as float)                                       as temp_max,
        cast(pressure        as int)                                         as pressure,
        cast(humidity        as int)                                         as humidity,
        cast(wind_speed      as float)                                       as wind_speed,
        cast(wind_speed * 3.6 as float)                                      as wind_speed_kmh,
        md5(concat_ws('|', latitude::text, longitude::text, city_name))      as location_key,
        md5(concat_ws('|', weather_main, weather_description))               as condition_key,
        cast(wind_deg        as int)                                         as wind_deg,
        coalesce(cast(wind_gust as float), 0.0)                              as wind_gust,
        cast(cloudiness      as int)                                         as cloudiness,
        cast(visibility      as int)                                         as visibility,
        case when visibility is null then 'missing' else 'present' end       as visibility_flag,
        sunrise,
        sunset,
        date_trunc('hour', entry_date)                                       as observation_hour,
        md5(date_trunc('hour', current_timestamp)::text)                     as time_key,
        entry_date                                                    
    from source
),

deduplicated as (

    select
        *,
        row_number() over (
            partition by location_key, observation_hour
            order by entry_date desc
        ) as row_num
    from prepared
)

select
    *
from deduplicated
where row_num = 1