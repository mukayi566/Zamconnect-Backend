import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.supabase import supabase

try:
    res = supabase.table("citizens").select("id", count="exact").execute()
    print(f"Citizen count: {res.count}")
    if res.data:
        print("Recent records:")
        for r in res.data[:5]:
            print(r)
except Exception as e:
    print(f"Error: {e}")
