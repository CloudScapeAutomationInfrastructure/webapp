import os
from dotenv import load_dotenv
import boto3
import base64
import json
from botocore.exceptions import BotoCoreError, ClientError


load_dotenv()

def decrypt_kms_ciphertext(ciphertext_blob):
    """Decrypt encrypted KMS values."""
    try:
        kms_client = boto3.client('kms', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        response = kms_client.decrypt(
            CiphertextBlob=base64.b64decode(ciphertext_blob)
        )
        plaintext = response['Plaintext'].decode('utf-8')
        return plaintext
    except (BotoCoreError, ClientError) as e:
        print(f"Error decrypting KMS ciphertext: {e}")
        raise Exception("Failed to decrypt KMS ciphertext.")

class Config:
    
    DATABASE_URL = (
        decrypt_kms_ciphertext(os.getenv('DATABASE_URL_ENCRYPTED'))
        if os.getenv('DATABASE_URL_ENCRYPTED')
        else os.getenv('DATABASE_URL', 'sqlite:///default.db')  
    )

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

   
    SECRET_KEY = (
        decrypt_kms_ciphertext(os.getenv('SECRET_KEY_ENCRYPTED'))
        if os.getenv('SECRET_KEY_ENCRYPTED')
        else os.getenv('SECRET_KEY', 'default-secret-key')  
    )

   
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'default-s3-bucket')  
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1') 

    
    SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", 'default-sns-topic')  

    
    SENDGRID_API_KEY = (
        decrypt_kms_ciphertext(os.getenv('SENDGRID_API_KEY_ENCRYPTED'))
        if os.getenv('SENDGRID_API_KEY_ENCRYPTED')
        else os.getenv('SENDGRID_API_KEY', 'default-sendgrid-key')  
    )

    FROM_EMAIL = os.getenv('FROM_EMAIL', 'default@example.com')  
    REPLY_TO_EMAIL = os.getenv('REPLY_TO_EMAIL', 'replyto@example.com')  