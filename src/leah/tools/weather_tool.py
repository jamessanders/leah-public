from langchain_core.tools import tool

import requests
import json

@tool
def fetch_weather_info(latitude: float, longitude: float) -> dict:
    """
    Fetches current weather and daily forecast information for a given latitude and longitude using the NOAA NWS API.

    Args:
        latitude: The latitude for the location.
        longitude: The longitude for the location.

    Returns:
        A dictionary containing weather information or an error message.
    """
    try:
        # Step 1: Get the grid points for the given latitude and longitude
        points_url = f"https://api.weather.gov/points/{latitude},{longitude}"
        points_response = requests.get(points_url)
        points_response.raise_for_status()  # Raise an exception for bad status codes
        points_data = points_response.json()

        forecast_url = points_data['properties']['forecast']
        forecast_hourly_url = points_data['properties']['forecastHourly']

        # Step 2: Get the forecast using the forecast URL
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()

        # Step 3: Get the hourly forecast using the hourly forecast URL
        forecast_hourly_response = requests.get(forecast_hourly_url)
        forecast_hourly_response.raise_for_status()
        forecast_hourly_data = forecast_hourly_response.json()

        # Extract relevant information (this is a basic example, you might want more)
        current_weather = forecast_hourly_data['properties']['periods'][0] # Get the current hour's data
        daily_forecast = forecast_data['properties']['periods'] # Get all daily forecast periods

        weather_info = {
            "current": {
                "temperature": current_weather.get("temperature"),
                "temperatureUnit": current_weather.get("temperatureUnit"),
                "shortForecast": current_weather.get("shortForecast"),
                "detailedForecast": current_weather.get("detailedForecast")
            },
            "daily": []
        }

        # Add daily forecasts (grabbing a few days as an example)
        for day in daily_forecast[:5]: # Get the next 5 days
            weather_info["daily"].append({
                "name": day.get("name"),
                "temperature": day.get("temperature"),
                "temperatureUnit": day.get("temperatureUnit"),
                "shortForecast": day.get("shortForecast"),
                "detailedForecast": day.get("detailedForecast")
            })


        return weather_info

    except requests.exceptions.RequestException as e:
        return {"error": f"Error fetching weather data: {e}"}
    except json.JSONDecodeError:
        return {"error": "Error decoding JSON response from weather API."}
    except KeyError as e:
        return {"error": f"Could not find expected data in API response: {e}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

if __name__ == '__main__':
    # Example usage: Fetch weather for a specific location (e.g., near the Googleplex)
    # You would replace these with the actual latitude and longitude passed to the tool
    example_latitude = 37.4219999
    example_longitude = -122.0840575

    weather_data = fetch_weather_info(example_latitude, example_longitude)
    print(json.dumps(weather_data, indent=2))
