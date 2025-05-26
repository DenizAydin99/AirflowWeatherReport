# WeatherReportETL

This project is a batch processing ETL pipeline designed to fetch weather data from the [OpenWeatherMap API](https://openweathermap.org/). In this project, a star schema design was applied to demonstrate data modeling practices and PostgreSQL was utilized as a Data Warehouse. After fetching data from the API, the pipeline persists the data in a staging table to separate the staging area from the analysis-ready data. Afterwards, the pipeline applies transformations and performs data quality checks with dbt. After the quality checks, data will be moved to its final destination (dimension and fact tables).

This project is fully containerized and the entire workflow is orchestrated with Apache Airflow.


## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Data Transformations & Quality Checks](#data-transformations-quality-checks)
- [Containerization](#containerization)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Overview

1. **Extract:**  
   Python tasks in Airflow fetch current weather data for configured cities from the OpenWeatherMap API and write raw JSON into a landing table.
2. **Load:**
   Data is inserted into a PostgreSQL staging schema via Airflow’s `SQLExecuteQueryOperator` and Jinja templating.
3. **Transformations & Validations:**
   dbt applies transformations to produce dimension and fact tables in a star schema, then runs assertions to enforce data quality.
4. **Orchestration:**
   Apache Airflow schedules and monitors each step, handling retries, logging, and alerting.
   
## Project Structure

```
WeatherReportETL/
├── dags/
│   └── weather_etl_dag.py         # Main Airflow DAG definition
├── dbt/
│   ├── dbt_project.yml            # dbt project configuration
│   └── models/                    # dbt models and tests
├── docker-compose.yml             # Compose file defining all services
├── Dockerfile                     # Custom Airflow image build
├── .env                           # Environment variables (API keys, Fernet key)
└── README.md                      # Project documentation
```

## Setup & Installation

1. **Clone the Repository:**

   ```bash
   git clone <repository_url>
   cd WeatherReportETL
   ```

2. **Configure Environment Variables:**  
   Create the `.env` file in the project root with:

   ```env
   OPENWEATHERMAP_API_KEY=your_api_key_here
   OPENWEATHERMAP_API_URL=http://api.openweathermap.org/data/2.5/weather
   AIRFLOW__CORE__FERNET_KEY=your_fernet_key_here
   ```

3. **Build and Start Containers:**

   Stop any running stack and remove volumes:
   ```bash
   docker-compose down --remove-orphans
   ```

   Build and start the services:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

4. **Initialize the Airflow Database:**

   Run the initialization command:
   ```bash
   docker-compose run --rm airflow-webserver airflow db init
   ```

5. **Create an Admin User:**

   Create an Airflow admin user using the CLI:
   ```bash
   docker-compose run --rm airflow-webserver airflow users create \
     --username admin \
     --firstname Admin \
     --lastname User \
     --role Admin \
     --email admin@example.com \
     --password admin
   ```

## Configuration
   Make sure that you configure `dbt/profiles.yml` to point at the same Postgres service (host:postgres, port: 5432, user/password: airflow)
   
   Both Airflow services load environment variables from the `.env` file to ensure a consistent configuration, including the Fernet key used for encryption.
   
## Usage

1. **Access the Airflow UI:**  
   Open your browser and navigate to [http://localhost:8080](http://localhost:8080).  
   Log in using the admin credentials you created (e.g., `admin/admin`).

2. **Trigger the DAG:**  
   In the Airflow UI, enable and trigger the DAG.  
   Monitor task logs to verify that data is fetched, loaded, and verified successfully.

3. **Check Data in PostgreSQL:**  
   You can inspect the weather data directly by connecting to the PostgreSQL container:
   ```bash
   docker-compose exec postgres psql -U airflow -d airflow
   ```
   Then run:
   ```sql
   SELECT * FROM raw_schema_landing.weather_raw;
   ```

## Data Transformations & Quality Checks

dbt models in `dbt/models/` build your dimensions (`dim_location`, `dim_condition` and `dim_time`) and fact table (`fact_weather`).

dbt tests ensure non-null, uniqueness, and referential integrity on keys.

The Airflow DAG runs `dbt run` followed by `dbt test` automatically after staging.

## Containerization

- **Services:**

   -postgres: primary data warehouse (5432)

   -airflow-webserver: Airflow UI & API (8080)

   -airflow-scheduler: schedules and runs jobs

   -dbt: dbt services

   -metabase: BI layer for visualization (3000)

## Troubleshooting

- **No DAGs in the UI:**  
  Ensure that your DAG files are in the `dags/` directory and that there are no syntax errors
- **Database Connection Issues:**  
  Use service names (e.g., `postgres`) instead of `localhost` in your connection strings.
- **Fernet Key Errors:**  
  Make sure your Fernet key is correctly defined and consistent across services via the `.env` file.
- **Airflow UI 500 errors:**
  Make sure that you do not point at the same port with Metabase and Airflow, or create another PostgreSQL database for metabase

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
