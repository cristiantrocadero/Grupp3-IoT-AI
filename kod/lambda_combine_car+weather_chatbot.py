import json
import boto3
import urllib3
import logging
from datetime import datetime, timedelta

# Set up logging to CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)
http = urllib3.PoolManager()

# Constants for Rekognition model and geolocation API
CUSTOM_MODEL_ARN = (
    "arn:aws:rekognition:us-east-1:904233095489"
    ":project/carCleanliness/version/carCleanliness."
    "2025-04-08T10.16.40/1744100201251"
)
OPENCAGE_API_KEY = "96492111890640d2acdf64ac1193d650"

def lambda_handler(event, context):
    """Main Lambda handler triggered by Amazon Lex"""
    logger.info("Received event: %s", json.dumps(event))

    intent_name = event["sessionState"]["intent"]["name"]

    # Route to appropriate intent handler
    if intent_name == "CarCheck":
        return handle_car_cleanliness_check(event)

    elif intent_name == "GetWeather":
        return handle_weather_forecast(event)

    # Unknown intent fallback
    else:
        return respond_plaintext(
            f"Sorry, I don't recognize the intent '{intent_name}'.",
            intent_name,
            "Failed"
        )

# --- Car Cleanliness Check ---

def handle_car_cleanliness_check(event):
    """Handles the CarCheck intent by analyzing an image from S3"""
    try:
        intent_name = event["sessionState"]["intent"]["name"]
        image_url = event["sessionState"]["intent"]["slots"]["imguri"]["value"]["interpretedValue"]

        # Parse S3 bucket and key from provided URL
        bucket, key = parse_s3_url(image_url)
        if not bucket or not key:
            return respond_plaintext(f"Invalid S3 URL: {image_url}", intent_name, "Failed")

        # Run custom Rekognition model
        result_message = detect_car_cleanliness(bucket, key)
        return respond_plaintext(result_message, intent_name, "Fulfilled")

    except Exception as e:
        return respond_plaintext(f"Error: {str(e)}", intent_name, "Failed")

def parse_s3_url(s3_url):
    """Parses an S3 URL into bucket and key"""
    prefix = "s3://"
    if not s3_url.lower().startswith(prefix):
        return None, None
    parts = s3_url[len(prefix):].split("/", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (None, None)

def detect_car_cleanliness(bucket, key):
    """Uses a custom Amazon Rekognition model to assess car cleanliness"""
    rekognition = boto3.client("rekognition", region_name="us-east-1")
    try:
        response = rekognition.detect_custom_labels(
            ProjectVersionArn=CUSTOM_MODEL_ARN,
            Image={"S3Object": {"Bucket": bucket, "Name": key}},
            MinConfidence=50.0  # Adjust threshold if needed
        )
        labels = response.get("CustomLabels", [])
        if not labels:
            return "Please check the car manually, my confidence level is too low."
        label = labels[0]
        return f"The car is {label['Name']} (with a confidence of {label['Confidence']:.1f}%)."
    except Exception as e:
        return f"Rekognition error: {str(e)}"

# --- Weather Forecast ---

def handle_weather_forecast(event):
    """Handles the GetWeather intent by retrieving a forecast from SMHI"""
    try:
        slots = event['sessionState']['intent']['slots']
        city = slots.get('City', {}).get('value', {}).get('interpretedValue')
        date = slots.get('Date', {}).get('value', {}).get('interpretedValue')

        # Prompt for missing slots
        if not city and not date:
            return elicit_slot(event, "City", "Which city would you like the weather for?")
        if not city:
            return elicit_slot(event, "City", "Which city?")
        if not date:
            return elicit_slot(event, "Date", "What date?")

        # Handle relative dates
        if date.lower() == "today":
            date = datetime.utcnow().strftime("%Y-%m-%d")
        elif date.lower() == "tomorrow":
            date = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")

        # Get city coordinates and forecast
        lon, lat = get_coordinates(city)
        if not lon or not lat:
            return respond_plaintext(f"Could not find coordinates for {city}.", "GetWeather", "Failed")

        weather_data = fetch_weather_data(lon, lat, date)
        if not weather_data:
            return respond_plaintext(f"No weather data found for {city} on {date}.", "GetWeather", "Failed")

        return respond_weather(weather_data, city, date)

    except Exception as e:
        return respond_plaintext(f"Error: {str(e)}", "GetWeather", "Failed")

def get_coordinates(city):
    """Fetches latitude and longitude for a given city using OpenCage API"""
    url = f"https://api.opencagedata.com/geocode/v1/json?q={city}&key={OPENCAGE_API_KEY}"
    response = http.request('GET', url)
    if response.status == 200:
        data = json.loads(response.data.decode('utf-8'))
        if data['results']:
            geometry = data['results'][0]['geometry']
            return geometry['lng'], geometry['lat']
    return None, None

def fetch_weather_data(lon, lat, date):
    """Fetches weather data from SMHI for given coordinates and date"""
    url = f"https://opendata-download-metfcst.smhi.se/api/category/pmp3g/version/2/geotype/point/lon/{round(lon, 4)}/lat/{round(lat, 4)}/data.json"
    response = http.request('GET', url)
    if response.status == 200:
        forecast = json.loads(response.data.decode('utf-8'))
        for entry in forecast.get("timeSeries", []):
            if entry["validTime"] == f"{date}T18:00:00Z":
                temp = rain = wind = "N/A"
                for param in entry["parameters"]:
                    if param["name"] == "t": temp = param["values"][0]
                    elif param["name"] == "pmean": rain = param["values"][0]
                    elif param["name"] == "ws": wind = param["values"][0]
                return {"temperature": temp, "rainfall": rain, "wind_speed": wind}
    return None

# --- Helpers for Responses ---

def respond_plaintext(msg, intent, state):
    """Builds a simple plain text response for Lex"""
    return {
        "sessionState": {
            "dialogAction": { "type": "Close" },
            "intent": { "name": intent, "state": state }
        },
        "messages": [
            { "contentType": "PlainText", "content": msg }
        ]
    }

def respond_weather(data, city, date):
    """Formats weather forecast into a user-friendly message"""
    msg = (
        f"The weather forecast for {city} on {date}:\n"
        f" Temperature: {data['temperature']}°C\n"
        f" Rainfall: {data['rainfall']} mm\n"
        f" Wind Speed: {data['wind_speed']} m/s"
    )
    return respond_plaintext(msg, "GetWeather", "Fulfilled")

def elicit_slot(event, slot, prompt):
    """Prompts user for a missing slot in the conversation"""
    return {
        "sessionState": {
            "dialogAction": { "type": "ElicitSlot", "slotToElicit": slot },
            "intent": event["sessionState"]["intent"]
        },
        "messages": [ { "contentType": "PlainText", "content": prompt } ]
    }
