import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
)

bucket_name = os.getenv("LOG_BUCKET_NAME")

# List objects
response = s3.list_objects_v2(Bucket=bucket_name, Prefix="logs/")
if 'Contents' in response:
    # Get latest file
    latest_file = max(response['Contents'], key=lambda x: x['LastModified'])
    key = latest_file['Key']
    
    # Read content
    obj = s3.get_object(Bucket=bucket_name, Key=key)
    print(f"--- Reading {key} ---")
    print(obj['Body'].read().decode('utf-8'))
else:
    print("No logs found.")