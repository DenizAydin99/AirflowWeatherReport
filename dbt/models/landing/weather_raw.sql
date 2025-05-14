{{  
    config(
        materialized = 'table',
        tags         = ['landing'],
    )
}}

select
    null::text   as country,
    null::text   as city_name,
    null::numeric as latitude,
    null::numeric as longitude,
    null::text   as weather_main,
    null::text   as weather_description,
    null::numeric as temp,
    null::numeric as feels_like,
    null::numeric as temp_min,
    null::numeric as temp_max,
    null::integer as pressure,
    null::integer as humidity,
    null::numeric as wind_speed,
    null::integer as wind_deg,
    null::numeric as wind_gust,
    null::integer as cloudiness,
    null::integer as visibility,
    null::timestamp as sunrise,
    null::timestamp as sunset,
    current_timestamp as entry_date     
where false                                -- produces 0 rows; the table structure is what we need