# WeatherReportETL

This project is an ETL pipeline designed to fetch weather data from the [OpenWeatherMap API](https://openweathermap.org/), perform data quality checks, and load the data into a PostgreSQL database. The entire workflow is orchestrated using Apache Airflow and containerized with Docker and Docker Compose.

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Data Quality Checks](#data-quality-checks)
- [Containerization](#containerization)
- [Troubleshooting](#troubleshooting)
- [Future Enhancements](#future-enhancements)
- [License](#license)

## Overview

The ETL pipeline consists of two main tasks:
1. **Data Extraction:**  
   Fetch weather data for a list of cities from the OpenWeatherMap API using a Python function.
2. **Data Loading:**  
   Load the extracted weather data into a PostgreSQL database using Airflow’s `SQLExecuteQueryOperator` and Jinja templating.

A post-load verification task then runs a SQL query (`SELECT * FROM weather`) and logs the contents of the table to ensure the data is loaded correctly.

## Project Structure

```
WeatherReportETL/
├── dags/
│   └── weather_etl_dag.py      # Airflow DAG file defining ETL tasks
├── docker-compose.yml          # Docker Compose file to orchestrate Airflow and PostgreSQL containers
├── Dockerfile                  # Dockerfile for building the Airflow container image
├── .env                        # Environment file for sensitive configuration (e.g., API keys, Fernet key)
└── README.md                   # Project README (this file)
```

## Setup & Installation

1. **Clone the Repository:**

   ```bash
   git clone <repository_url>
   cd WeatherReportETL
   ```

2. **Configure Environment Variables:**  
   Create and update the `.env` file with your settings. For example:

   ```env
   OPENWEATHERMAP_API_KEY=your_api_key_here
   OPENWEATHERMAP_API_URL=http://api.openweathermap.org/data/2.5/weather
   AIRFLOW__CORE__FERNET_KEY=your_fernet_key_here
   ```

3. **Build and Start Containers:**

   Bring down any previous containers:
   ```bash
   docker-compose down --remove-orphans
   ```

   Build and start the services:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

4. **Initialize the Airflow Database:**

   Run the initialization command (use the webserver service or scheduler service as both share the image):
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

- **Docker Compose:**  
  The `docker-compose.yml` file defines three services:
  - **postgres:** Runs PostgreSQL 13 with the specified user, password, and database.
  - **airflow-webserver:** Runs the Airflow webserver.
  - **airflow-scheduler:** Runs the Airflow scheduler.

  Both Airflow services load environment variables from the `.env` file to ensure a consistent configuration, including the Fernet key used for encryption.

- **DAGs:**  
  Place your DAG files in the `dags/` folder. The sample DAG (`weather_etl_dag.py`) contains tasks to fetch weather data, load it into PostgreSQL, and verify the load.

## Usage

1. **Access the Airflow UI:**  
   Open your browser and navigate to [http://localhost:8080](http://localhost:8080).  
   Log in using the admin credentials you created (e.g., `admin/admin`).

2. **Trigger the DAG:**  
   In the Airflow UI, enable and trigger the `weather_etl` DAG.  
   Monitor task logs to verify that data is fetched, loaded, and verified successfully.

3. **Check Data in PostgreSQL:**  
   You can inspect the weather data directly by connecting to the PostgreSQL container:
   ```bash
   docker-compose exec postgres psql -U airflow -d airflow
   ```
   Then run:
   ```sql
   SELECT * FROM weather;
   ```

## Data Quality Checks

After loading data, a verification task runs a SQL query to fetch all rows from the `weather` table and logs the result. This helps ensure that:
- Data is inserted as expected.
- The ETL process is operating correctly.

## Containerization

- **Docker & Docker Compose:**  
  The project uses Docker Compose to orchestrate all components, ensuring a consistent environment.  
- **Volumes:**  
  The `./dags` and `./logs` folders are mounted into the container to allow real-time updates and persistent logging.
- **Health Checks:**  
  The PostgreSQL service includes a health check (`pg_isready`) to ensure it's ready before Airflow starts.

## Troubleshooting

- **No DAGs in the UI:**  
  Ensure your DAG files are in the `dags/` directory on your host so they are correctly mounted into the container.
- **Database Connection Issues:**  
  Use service names (e.g., `postgres`) instead of `localhost` in your connection strings.
- **Fernet Key Errors:**  
  Make sure your Fernet key is correctly defined and consistent across services via the `.env` file.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
