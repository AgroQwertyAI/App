import requests

def create_admin_user():
    print("Create Admin User")
    print("-----------------")
    
    username = input("Username: ")
    password = input("Password: ")
    name = input("Full Name: ")
    
    # Prepare request data
    payload = {
        "username": username,
        "password": password,
        "name": name,
        "role": "admin"
    }
    
    # Send request
    try:
        response = requests.post("http://localhost:8000/create_user", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Admin user created successfully!")
            print(f"Username: {result['username']}")
            print(f"Role: {result['role']}")
            print(f"User ID: {result['id']}")
        else:
            print(f"Error: {response.json().get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"Failed to connect to server: {e}")

if __name__ == "__main__":
    create_admin_user()