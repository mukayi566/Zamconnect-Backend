import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.supabase import supabase

email = "admin@zamid.gov.zm"

print(f"Checking for user: {email}")

try:
    # Check auth users
    # Note: supabase.auth.admin.list_users() requires service role
    users_res = supabase.auth.admin.list_users()
    users = users_res
    target_user = next((u for u in users if u.email == email), None)
    
    if target_user:
        print(f"Auth user found: ID={target_user.id}, Confirmed={target_user.email_confirmed_at}")
        
        # Check admin_users table
        admin_res = supabase.table("admin_users").select("*").eq("id", target_user.id).execute()
        if admin_res.data:
            print(f"Admin record found: {admin_res.data[0]}")
        else:
            print("No admin record found in 'admin_users' table.")
    else:
        print("Auth user NOT found.")

except Exception as e:
    print(f"Error: {e}")
