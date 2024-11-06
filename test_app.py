import json
from io import BytesIO

def test_create_user_success(client):
    # User data payload
    payload = {
        "email": "test@example.com",
        "password": "strongpassword",
        "first_name": "Test",
        "last_name": "User"
    }

    # Create a sample image file to upload
    image_data = BytesIO(b"test image data")
    image_data.name = "test_image.jpg"  # Simulate a file name

    # Send POST request with data and file
    response = client.post(
        '/v1/user',
        data={
            **payload,  # Unpack the payload dictionary
            "file": (image_data, "test_image.jpg")
        },
        content_type='multipart/form-data'
    )

    # Validate the response
    assert response.status_code == 201

    response_data = response.get_json()

    # Check returned data fields
    assert response_data['email'] == "test@example.com"
    assert response_data['first_name'] == "Test"
    assert response_data['last_name'] == "User"
    assert 'account_created' in response_data
    assert 'account_updated' in response_data


def test_create_user_already_exists(client):
    # User data payload
    payload = {
        "email": "test@example.com",
        "password": "strongpassword",
        "first_name": "Test",
        "last_name": "User"
    }

    # First request to create user
    response = client.post('/v1/user', data=payload, content_type='multipart/form-data')
    assert response.status_code == 201  

    # Second request with the same payload to check duplicate user creation
    response = client.post('/v1/user', data=payload, content_type='multipart/form-data')

    # Validate the response for duplicate user
    assert response.status_code == 400
    assert response.get_json()['error'] == "User already exists"


def test_get_user_success(client, auth_headers):
    # Assume user has been created and `auth_headers` provides valid authentication headers

    response = client.get('/v1/user/self', headers=auth_headers)

    # Validate the response
    assert response.status_code == 200
    response_data = response.get_json()

    # Check returned data fields
    assert response_data['email'] == "test@example.com"
    assert response_data['first_name'] == "Test"
    assert response_data['last_name'] == "User"
    assert 'account_created' in response_data
    assert 'account_updated' in response_data
