import requests
import os
from dotenv import load_dotenv
import psycopg2
import time

# Load the .env file
load_dotenv()

# Get the API key from the .env file
API_KEY = os.getenv("WEATHERSTACK_API_KEY")

# Database connection settings
DB_HOST = "localhost"
DB_NAME = "weather_data"
DB_USER = "denizaydin"

# Connect to PostgreSQL
try:
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER
    )
    cur = conn.cursor()
    print("Successfully connected to PostgreSQL!")
except Exception as e:
    print(f"Database connection failed: {e}")
    exit()

cities = ["New York", "London", "Istanbul", "Tokyo"]

# Request for each city
for city in cities:
    params = {
        "access_key": API_KEY,
        "query": city,
        "units": "m"
    }
    response = requests.get("http://api.weatherstack.com/current", params=params)

    if response.status_code == 200:
        data = response.json()

        # Ensure API returned data correctly
        if "location" in data and "current" in data:
            temperature = data["current"]["temperature"]
            humidity = data["current"]["humidity"]
            wind_speed = data["current"]["wind_speed"]
            description = data["current"]["weather_descriptions"][0]

            # Insert data into PostgreSQL
            try:
                cur.execute("""
                    INSERT INTO weather (city, temperature, humidity, wind_speed, description)
                    VALUES (%s, %s, %s, %s, %s);
                """, (city, temperature, humidity, wind_speed, description))

                conn.commit()
                print(f"Data inserted for {city}!")
            except Exception as e:
                print(f"Error inserting data for {city}: {e}")
                conn.rollback()
        else:
            print(f"API response did not contain expected data for {city}: {data}")
    else:
        print(f"API Request Failed for {city}: {response.status_code}, {response.text}")

    time.sleep(1)

cur.close()
conn.close()