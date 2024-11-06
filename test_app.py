import json

def test_create_user_success(client):
   
    payload = {
        "email": "test@example.com",
        "password": "strongpassword",
        "first_name": "Test",
        "last_name": "User"
    }

   
    response = client.post('/v1/user', data=json.dumps(payload), content_type='application/json')

    
    assert response.status_code == 201

    
    response_data = response.get_json()

    
    assert response_data['email'] == "test@example.com"
    assert response_data['first_name'] == "Test"
    assert response_data['last_name'] == "User"
    assert 'account_created' in response_data
    assert 'account_updated' in response_data



def test_create_user_already_exists(client):
    
    payload = {
        "email": "test@example.com",
        "password": "strongpassword",
        "first_name": "Test",
        "last_name": "User"
    }

    
    response = client.post('/v1/user', data=json.dumps(payload), content_type='application/json')
    assert response.status_code == 201  
    
    response = client.post('/v1/user', data=json.dumps(payload), content_type='application/json')

    
    assert response.status_code == 400
    assert response.get_json()['error'] == "User already exists"

    #end of file