FROM apache/airflow:2.10.5-python3.10

USER root

# Installs required system packages
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Switches back to airflow user
USER airflow

COPY .env /opt/airflow/.env
COPY dags/weather_etl_dag.py /opt/airflow/dags/

RUN pip install dbt-postgres==1.9.0