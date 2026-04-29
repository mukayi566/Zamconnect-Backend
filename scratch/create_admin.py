import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.supabase import supabase

email = "admin@zamid.gov.zm"
password = "ZamID@2026!"

print("Creating admin user...")

user_id = None
try:
    response = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True
    })
    user_id = response.user.id
    print(f"Created auth user with ID: {user_id}")
except Exception as e:
    print(f"Auth user might already exist, attempting login. Error: {e}")
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user_id = res.user.id
        print(f"User already exists, obtained ID: {user_id}")
    except Exception as e2:
        print(f"Could not authenticate to get ID: {e2}")
        sys.exit(1)

if not user_id:
    print("Failed to get user ID.")
    sys.exit(1)

# Try inserting into admin_users table
admin_data = {
    "id": user_id,
    "email": email,
    "role": "admin",
    "full_name": "System Administrator"
}

print(f"Inserting into admin_users table: {admin_data}")
try:
    insert_res = supabase.table("admin_users").insert(admin_data).execute()
    print("Successfully inserted into admin_users table.")
    print(insert_res.data)
except Exception as e:
    print(f"Error inserting into admin_users: {e}")
    if "column" in str(e).lower() and "email" in str(e).lower():
        print("Retrying without 'email' field...")
        admin_data.pop("email")
        try:
            insert_res2 = supabase.table("admin_users").insert(admin_data).execute()
            print("Successfully inserted into admin_users table (without email).")
            print(insert_res2.data)
        except Exception as e3:
            print(f"Still failing: {e3}")
