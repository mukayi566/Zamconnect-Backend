import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.supabase import supabase

email = "admin@zamid.gov.zm"
password = "ZamID@2026!"

print(f"Attempting login for: {email}")

try:
    response = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })
    
    if response.user:
        print(f"Login SUCCESS! User ID: {response.user.id}")
    else:
        print("Login FAILED. No user returned.")

except Exception as e:
    print(f"Login FAILED with exception: {e}")
