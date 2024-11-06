import json
from io import BytesIO

def test_create_user_success(client):
    # Form data payload
    data = {
        "email": "test@example.com",
        "password": "strongpassword",
        "first_name": "Test",
        "last_name": "User"
    }

    # Simulate an image file upload
    data_with_file = {
        **data,
        "file": (BytesIO(b"fake image content"), "test_image.jpg")
    }

    # Send the POST request as form data with a file
    response = client.post(
        '/v1/user', 
        data=data_with_file,
        content_type='multipart/form-data'
    )

    assert response.status_code == 201
    response_data = response.get_json()
    assert response_data['email'] == "test@example.com"
    assert response_data['first_name'] == "Test"
    assert response_data['last_name'] == "User"
    assert 'account_created' in response_data
    assert 'account_updated' in response_data


def test_create_user_already_exists(client):
    data = {
        "email": "test@example.com",
        "password": "strongpassword",
        "first_name": "Test",
        "last_name": "User"
    }

    # First request to create the user
    response = client.post(
        '/v1/user', 
        data=data,
        content_type='multipart/form-data'
    )
    assert response.status_code == 201

    # Second request with the same email to trigger the "User already exists" error
    response = client.post(
        '/v1/user', 
        data=data,
        content_type='multipart/form-data'
    )
    assert response.status_code == 400
    assert response.get_json()['error'] == "User already exists"
