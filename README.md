# Car & Weather Chatbot

## Overview

This documentation provides a step-by-step guide on setting up and running a car cleanliness and weather assistant using AWS services (Lex, Rekognition, S3) and Streamlit as the front-end interface. The application allows users to interact with a chatbot, view image results from Rekognition, and get weather forecasts for specific cities and dates.

---

## Prerequisites

- AWS Account
- Python 3.8 or higher
- AWS CLI installed and configured
- Basic knowledge of Python, AWS Services, and command line operations

---

## Technologies Used

- **AWS Lex**: For handling chatbot conversations.
- **AWS Rekognition**: For analyzing car cleanliness from S3 images.
- **AWS S3**: For storing and retrieving car images.
- **AWS Lambda**: For backend logic and integration of Rekognition and weather APIs.
- **Streamlit**: For building the interactive front-end interface.
- **OpenCage API**: For converting city names into coordinates.
- **SMHI API**: For fetching weather data.

---

## Setup Instructions

### Step 1: Setting Up AWS Services

#### AWS S3 Bucket

Create a bucket to store images of cars (e.g., in folders `Test/clean/` and `Test/dirty/`):

```bash
aws s3 mb s3://your-bucket-name --region your-region
```

#### AWS Lex Bot

1. Go to [Amazon Lex](https://console.aws.amazon.com/lex/).
2. Create a bot and define the following intents:
   - `CarCheck`: Triggered when user asks about the cleanliness of a car.
   - `GetWeather`: Triggered when user asks about the weather in a specific city and date.

#### AWS Rekognition

Use a pre-trained custom model via `detect_custom_labels` to classify images as `Clean` or `Dirty`. The model is called programmatically from a Lambda function.

---

### Step 2: Setting Up the Environment

#### Clone the Repository

```bash
git clone <your-repository-url>
cd <project-folder>
```

#### Install Dependencies

```bash
pip install -r requirements.txt
```

Contents of `requirements.txt`:

```txt
boto3
botocore
streamlit
Pillow
requests
```

---

### Step 3: Streamlit Application Setup

Run the app locally:

```bash
streamlit run app.py
```

The app will open at [http://localhost:8501](http://localhost:8501)

---

### Step 4: Integrating AWS Services

#### AWS Lex Integration

The chatbot component connects directly to your Lex bot using `boto3`'s `lexv2-runtime` client. It maintains session history in Streamlit and displays chat messages interactively.

#### AWS Rekognition Integration

After users upload or reference images via S3 URIs (e.g., `s3://your-bucket/Test/dirty/image1.jpg`), the Lambda function will run a prediction using a custom Rekognition model.

#### Image Upload to S3 (Example Code)

```python
import boto3

def upload_to_s3(file, bucket, object_name=None):
    if object_name is None:
        object_name = file.name
    s3_client = boto3.client('s3')
    response = s3_client.upload_fileobj(file, bucket, object_name)
    return response
```

---

### Step 4.1: Lambda Function

The `lambda_combine_car+weather_chatbot.py` file contains the logic for:

- Parsing S3 image URIs and sending them to Rekognition
- Calling OpenCage to get coordinates from city names
- Fetching weather forecasts from SMHI API
- Returning chatbot responses to Lex for display in Streamlit

---

## Running the Application

1. Launch the app:
   ```bash
   streamlit run app.py
   ```

2. In your browser:
   - 💬 **Weather Forecast (GetWeather intent)**:
     1. Start by saying: `"What is the weather?"`
     2. The bot will ask: `"Which city do you want to know?"` → respond with e.g. `"Gothenburg"`
     3. Then: `"What date do you need?"` → respond with e.g. `"today"`
   
   - 🚗 **Car Cleanliness Check (CarCheck intent)**:
     1. Start by asking: `"Does the car that just entered need cleaning?"`
     2. The bot will ask: `"Provide image URI (from your s3), please."` → respond with e.g.:
        ```
        s3://grupp3-carwash/Test/clean/bil27.png
        ```

   - 🖼️ **View Images**:
     - Browse the latest images under `Test/clean` and `Test/dirty` categories stored in your S3 bucket.

---

## Security Note

Do not expose your AWS credentials in the codebase. Use environment variables or AWS Secrets Manager in production environments.

---

## Authors

YH-Akademin BI med AI Program 2024 - Group 3 - Cristian Troncoso, Tobias Englund, John Hagström & Valle Andersson
