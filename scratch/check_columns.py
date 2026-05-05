from app.config.supabase import supabase
import json

try:
    res = supabase.table("citizens").select("*").limit(1).execute()
    if res.data:
        print(json.dumps(list(res.data[0].keys()), indent=2))
    else:
        print("No data in citizens table")
except Exception as e:
    print(f"Error: {e}")
