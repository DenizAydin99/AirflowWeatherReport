FROM apache/airflow:2.10.5-python3.10

COPY .env /opt/airflow/.env
COPY weather_etl_dag.py /opt/airflow/dags/