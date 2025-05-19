import os
import logging
import requests
import psycopg2
from dotenv import load_dotenv
from datetime import timedelta, datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
import pendulum
import socket
from airflow.operators.bash import BashOperator

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
API_URL = os.getenv("OPENWEATHERMAP_API_URL")

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
    {"lat": 41.39, "lon": 2.17, "cityName": "Barcelona"}
]

weather_data_list = []

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
    "weather_etl_pipeline",
    default_args=default_args,
    description="ETL pipeline: Extracts weather data, stages it, then loads into star schema.",
    schedule_interval=timedelta(days=1),
    catchup=False,
)

def get_weather_data(**kwargs):
    local_data = []
    try:
        socket.create_connection(("api.openweathermap.org", 80), timeout=5)
    except OSError:
        logging.error("Network connection test failed.")
        return False

    for city in cities:
        params = {"appid": API_KEY, "units": "metric", "lat": city["lat"], "lon": city["lon"]}
        try:
            response = requests.get(API_URL, params=params, timeout=10)
            response.raise_for_status()
            #print('response is:%s',response)
            data = response.json()
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
                'wind_gust': data["wind"].get("gust", None),
                'cloudiness': data["clouds"]["all"],
                'visibility': data["visibility"],
                'sunrise': datetime.fromtimestamp(data["sys"]["sunrise"]),
                'sunset': datetime.fromtimestamp(data["sys"]["sunset"]),
                'entry_date': datetime.now()
            }
            local_data.append(weather_data)
        except Exception as e:
            logging.error(f"Failed for city {city['cityName']}: {e}")
            continue

    kwargs['ti'].xcom_push(key="weather_data_list", value=local_data)

def load_to_landing(**kwargs):
    data_list = kwargs['ti'].xcom_pull(task_ids='get_weather_data', key='weather_data_list')
    if not data_list:
        logging.info("No data to insert into staging.")
        return

    conn = psycopg2.connect("dbname=airflow user=airflow password=airflow host=postgres")
    cur = conn.cursor()

    insert_query = """
        INSERT INTO raw_schema_landing.weather_raw (
            country, city_name, latitude, longitude, weather_main, weather_description,
            temp, feels_like, temp_min, temp_max, pressure, humidity,
            wind_speed, wind_deg, wind_gust, cloudiness, visibility, sunrise, sunset, entry_date
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    for record in data_list:
        cur.execute(insert_query, (
            record['country'], record['city_name'], record['latitude'], record['longitude'],
            record['weather_main'], record['weather_description'], record['temp'],
            record['feels_like'], record['temp_min'], record['temp_max'],
            record['pressure'], record['humidity'], record['wind_speed'],
            record['wind_deg'], record['wind_gust'], record['cloudiness'],
            record['visibility'], record['sunrise'], record['sunset'], record['entry_date']
        ))

    try:
        conn.commit()
        logging.info(f"{len(data_list)} records loaded into staging")

    except Exception as e:
        logging.error(f"Error committing to database: {e}")
        conn.rollback()

    cur.close()
    conn.close()

# Initialize the folder for dbt packages
init_dbt_packages = BashOperator(
    task_id="init_dbt_packages",
    bash_command="mkdir -p /opt/airflow/dbt/dbt_packages",
    dag=dag,
)

# Step 1: dbt packages
execute_dbt_deps = BashOperator(
    task_id="dbt_deps",
        bash_command="cd /opt/airflow/dbt && dbt deps",
    dag=dag,
)

# Step 2: dbt health check
execute_dbt_debug = BashOperator(
    task_id="dbt_debug",
        bash_command="cd /opt/airflow/dbt && dbt debug --target dev",
    dag=dag,
)

# Loads data to landing table
execute_dbt_run_landing = BashOperator(
    task_id="dbt_run_landing",
    bash_command="cd /opt/airflow/dbt && dbt run --select tag:landing",
    dag=dag,
)

# Performs transformations in staging table
execute_dbt_run_stg = BashOperator(
    task_id="dbt_run_stg",
        bash_command="cd /opt/airflow/dbt && dbt run --select tag:stg",
    dag=dag,
)

# Creates and populates dim tables
execute_dbt_run_dim = BashOperator(
    task_id="dbt_run_dim",
        bash_command="cd /opt/airflow/dbt && dbt run --select tag:dim",
    dag=dag,
)

# Creates and populates fact tables
execute_dbt_run_fact = BashOperator(
    task_id="dbt_run_fact",
        bash_command="cd /opt/airflow/dbt && dbt run --select tag:fact",
    dag=dag,
)

# Calls the API for data extraction
execute_get_weather_data = PythonOperator(
    task_id="get_weather_data",
    python_callable=get_weather_data,
    dag=dag,
)

# Loads data into the landing table
execute_load_staging = PythonOperator(
    task_id="load_to_landing",
    python_callable=load_to_landing,
    dag=dag,
)

execute_dbt_run_hist = BashOperator (
    task_id="dbt_run_hist",
    bash_command="cd /opt/airflow/dbt && dbt run --select tag:fact_hist",
    dag=dag,
)

init_dbt_packages >> execute_get_weather_data >> execute_dbt_deps >> execute_dbt_debug >> execute_dbt_run_landing >> execute_load_staging >> execute_dbt_run_stg >> execute_dbt_run_dim >> execute_dbt_run_fact >> execute_dbt_run_hist
