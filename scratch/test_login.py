import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'app'))
from app.config.supabase import supabase
from app.services.token_service import create_access_token

def test_login():
    email = "test@example.com"
    password = "password"
    
    try:
        print(f"Attempting to sign in with {email}...")
        # Note: This might fail if the user doesn't exist, which is fine
        # We just want to see if the call itself crashes
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error during sign in: {e}")

if __name__ == "__main__":
    test_login()
