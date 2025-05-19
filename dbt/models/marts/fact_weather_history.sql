{{ config(
    materialized = "incremental",
    unique_key   = ["entry_date", "location_key"],
    tags         = ["fact_hist"]
) }}

with latest as (
  select * from {{ ref('stg_weather_raw') }}
)

select
  country,
  city_name,
  latitude,
  longitude,
  weather_main,
  weather_description,
  temp,
  temp_fahrenheit,
  feels_like,
  temp_min,
  temp_max,
  pressure,
  humidity,
  wind_speed,
  wind_speed_kmh,
  location_key,
  condition_key,
  wind_deg,
  wind_gust,
  cloudiness,
  visibility,
  visibility_flag,
  sunrise,
  sunset,
  observation_hour,
  time_key,
  entry_date
from latest

{% if is_incremental() %}
where (entry_date, location_key) not in (
  select entry_date, location_key from {{ this }}
)
{% endif %}