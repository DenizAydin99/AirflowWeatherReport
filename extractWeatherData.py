import os
import logging
import requests
from dotenv import load_dotenv
from datetime import timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
import pendulum
import socket
from requests.exceptions import Timeout, ConnectionError
from _scproxy import _get_proxy_settings

# Had to add this because of a python bug on MacOS
_get_proxy_settings()
os.environ['NO_PROXY'] = '*'

# Loads environment variables (API_KEY) from an environment file
load_dotenv()

API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

AIRFLOW_PG_CONN_ID = "postgres_default"

# Specify the cities to fetch weather data for
cities = [
    {"lat": 51.51, "lon": 0.12, "cityName": "London"},
    {"lat": 35.67, "lon": 139.65, "cityName": "Tokyo"},
    {"lat": 48.85, "lon": 2.35, "cityName": "Paris"},
    {"lat": 52.36, "lon": 4.90, "cityName": "Amsterdam"},
    {"lat": 43.71, "lon": 7.26, "cityName": "Nice"},
    {"lat": 50.11, "lon": 8.68, "cityName": "Frankfurt"},
    {"lat": 53.55, "lon": 9.99, "cityName": "Hamburg"},
    {"lat": 40.71, "lon": 74.00, "cityName": "New York"},
    {"lat": 41.90, "lon": 12.48, "cityName": "Rome"},
    {"lat": 53.35, "lon": 6.26, "cityName": "Dublin"},
    {"lat": 41.01, "lon": 28.98, "cityName": "Istanbul"},
    {"lat": 40.42, "lon": 3.70, "cityName": "Madrid"},
    {"lat": 41.39, "lon": 2.17, "cityName": "Barcelona"},
]

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": pendulum.today('UTC').add(days=-1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "weather_etl",
    default_args=default_args,
    description="ETL pipeline to fetch weather data and store in PostgreSQL",
    schedule_interval=timedelta(days=1),
    catchup=False,
)

# Did not modulize the function further as the free version of OpenWeatherMap API had to be called for each city separately,
# and the response had to be parsed for each city separately. So it was easier to follow the logic as it is
def get_weather_data(**kwargs):
    weather_data_list =[]
    data=''
    try:
        socket.create_connection(("api.openweathermap.org", 80), timeout=5)
        logging.info("Network connection test successful")
    except OSError:
        logging.error(
            "Network connection test failed: Unable to reach OpenWeatherMap API")
        return False
    logging.info(f"API Key: {API_KEY}")

    for city in cities:
        params = {
            "appid": API_KEY,
            "units": "metric",
            "lat": city["lat"],
            "lon": city["lon"]
        }
        logging.info(f"params: {params}")
        try:
            logging.info(f"trying to extract from API for {city}")
            try:
                response = requests.get(
                    "http://api.openweathermap.org/data/2.5/weather", params=params, timeout=10)
                logging.info(f"API Response was: {response}")
                response.raise_for_status()
            except Timeout:
                logging.error(f"API Request Timeout for {city}")
                continue
            except ConnectionError:
                logging.error(f"API Connection Error for {city}")
                continue
            except Exception as e:
                logging.error(f"API Request Failed for {city}: {e}")
                continue

            logging.info(f"API Status Code: {response.status_code}")
            data = response.json()
            logging.info(f"Received response: {data}")

            # Extracts fields from API response
            weather_data = {
                'country': data["sys"]["country"],
                'city_name': data["name"],
                'latitude': data["coord"]["lat"],
                'longitude': data["coord"]["lon"],
                'weather_main': data["weather"][0]["main"],
                'weather_description': data["weather"][0]["description"],
                'temp': data["main"]["temp"],
                'feels_like': data["main"]["feels_like"],
                'temp_min': data["main"]["temp_min"],
                'temp_max': data["main"]["temp_max"],
                'pressure': data["main"]["pressure"],
                'humidity': data["main"]["humidity"],
                'wind_speed': data["wind"]["speed"],
                'wind_deg': data["wind"]["deg"],
                'wind_gust': data["wind"].get("gust", None), # handles missing gust values
                'cloudiness': data["clouds"]["all"],
                'visibility': data["visibility"],
                'sunrise': data["sys"]["sunrise"],
                'sunset': data["sys"]["sunset"]
            }
            logging.info(f"Response mapped to data: {weather_data}")
            weather_data_list.append(weather_data)
            logging.info(
                f"Appended to weather_data_list from weather_data: {weather_data_list}")
        except requests.exceptions.RequestException as e:
            logging.error(f"API Request Failed for {city}: {e}")
            continue
        logging.info(f"Weather Data Fetch Task Completed for {city}")

    kwargs['ti'].xcom_push(key="weather_data_list", value=weather_data_list)
    logging.info(f"Data successfully loaded into XCom: {weather_data_list}")


# Airflow Tasks -----------------------------------------------------------------------------------
execute_get_weather_data = PythonOperator(
    task_id="get_weather_data",
    python_callable=get_weather_data,
    provide_context=True,
    dag=dag,
)

# Loads weather data into PostgreSQL using XCom and Jinja templating
execute_load_weather_data = SQLExecuteQueryOperator(
    task_id="load_weather_data",
    conn_id=AIRFLOW_PG_CONN_ID,
    sql="""
    {% set weather_list = ti.xcom_pull(task_ids='get_weather_data', key='weather_data_list') or [] %}

    {% if weather_list | length > 0 %}
    INSERT INTO public.weather (
        country, city_name, latitude, longitude, weather_main, weather_description, temp, feels_like,
        temp_min, temp_max, pressure, humidity, wind_speed, wind_deg, wind_gust,
        cloudiness, visibility, sunrise, sunset
    ) VALUES
    {% for weather in weather_list -%}
    (
        '{{ weather["country"] }}',
        '{{ weather["city_name"] }}',
        {{ weather["latitude"] }},
        {{ weather["longitude"] }},
        '{{ weather["weather_main"] }}',
        '{{ weather["weather_description"] }}',
        {{ weather["temp"] }},
        {{ weather["feels_like"] }},
        {{ weather["temp_min"] }},
        {{ weather["temp_max"] }},
        {{ weather["pressure"] }},
        {{ weather["humidity"] }},
        {{ weather["wind_speed"] }},
        {{ weather["wind_deg"] }},
        {% if weather["wind_gust"] is not none %}
            {{ weather["wind_gust"] }}
        {% else %}
            NULL
        {% endif %},
        {{ weather["cloudiness"] }},
        {{ weather["visibility"] }},
        TO_TIMESTAMP({{ weather["sunrise"] }}),
        TO_TIMESTAMP({{ weather["sunset"] }})
    ){% if not loop.last %}, {% endif %}
    {% endfor %};
    {% else %}
    -- No data to insert
    SELECT 1;
    {% endif %}
    """,
    autocommit=True,
    dag=dag,
)

execute_get_weather_data >> execute_load_weather_data
