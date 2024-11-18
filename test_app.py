import json

# Test for successfully creating a user
def test_create_user_success(client):
    payload = {
        "email": "test@example.com",
        "password": "strongpassword",
        "first_name": "Test",
        "last_name": "User"
    }

    # Send POST request to create a user
    response = client.post('/v1/user', data=json.dumps(payload), content_type='application/json')

    # Assert the user is created successfully
    assert response.status_code == 201
    response_data = response.get_json()

    # Check the returned user details
    assert response_data['message'] == "User created successfully. Verification email sent."
    assert 'user_id' in response_data


# Test for handling duplicate user creation
def test_create_user_already_exists(client):
    payload = {
        "email": "test@example.com",
        "password": "strongpassword",
        "first_name": "Test",
        "last_name": "User"
    }

    # Send POST request to create the user
    response = client.post('/v1/user', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 201  # First creation should succeed

    # Send POST request again to create the same user
    response = client.post('/v1/user', data=json.dumps(payload), content_type='application/json')

    # Assert that the duplicate user is not allowed
    assert response.status_code == 400
    response_data = response.get_json()
    assert response_data['error'] == "User already exists"


# Test for missing fields
def test_create_user_missing_fields(client):
    payload = {
        "email": "test@example.com"
    }

    # Send POST request with missing fields
    response = client.post('/v1/user', data=json.dumps(payload), content_type='application/json')

    # Assert that the request is rejected due to missing fields
    assert response.status_code == 400
    response_data = response.get_json()
    assert "Missing required fields" in response_data['error']
