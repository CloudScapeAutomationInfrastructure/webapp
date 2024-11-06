import json
from io import BytesIO
from base64 import b64encode
import pytest
from moto import mock_s3
import boto3
import os

@pytest.fixture
def auth_headers():
    credentials = b64encode(b"test@example.com:strongpassword").decode("utf-8")
    return {
        "Authorization": f"Basic {credentials}"
    }

@pytest.fixture(scope='function')
def s3_mock(monkeypatch):
    with mock_s3():
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = os.getenv('S3_BUCKET_NAME', 'image-upload-s3-bucket-123')
        s3.create_bucket(Bucket=bucket_name)
        monkeypatch.setenv('S3_BUCKET_NAME', bucket_name)
        yield

def test_create_user_success(client, s3_mock):
    payload = {
        "email": "test@example.com",
        "password": "strongpassword",
        "first_name": "Test",
        "last_name": "User"
    }

    image_data = BytesIO(b"test image data")
    image_data.name = "test_image.jpg"

    response = client.post(
        '/v1/user',
        data={
            **payload,
            "file": (image_data, "test_image.jpg")
        },
        content_type='multipart/form-data'
    )

    assert response.status_code == 201
    response_data = response.get_json()

    assert response_data['email'] == "test@example.com"
    assert response_data['first_name'] == "Test"
    assert response_data['last_name'] == "User"
    assert 'account_created' in response_data
    assert 'account_updated' in response_data

def test_create_user_already_exists(client, s3_mock):
    payload = {
        "email": "test@example.com",
        "password": "strongpassword",
        "first_name": "Test",
        "last_name": "User"
    }

    response = client.post('/v1/user', data=payload, content_type='multipart/form-data')
    assert response.status_code == 201  

    response = client.post('/v1/user', data=payload, content_type='multipart/form-data')
    assert response.status_code == 400
    assert response.get_json()['error'] == "User already exists"

def test_get_user_success(client, auth_headers, s3_mock):
    # First, create the user for authentication
    payload = {
        "email": "test@example.com",
        "password": "strongpassword",
        "first_name": "Test",
        "last_name": "User"
    }
    client.post('/v1/user', data=payload, content_type='multipart/form-data')

    # Now retrieve the user profile with authentication headers
    response = client.get('/v1/user/self', headers=auth_headers)
    assert response.status_code == 200
    response_data = response.get_json()

    assert response_data['email'] == "test@example.com"
    assert response_data['first_name'] == "Test"
    assert response_data['last_name'] == "User"
    assert 'account_created' in response_data
    assert 'account_updated' in response_data
