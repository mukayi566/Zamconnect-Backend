import asyncio
from app.config.supabase import supabase

async def check_columns():
    try:
        # Try to get one record or just the column names by selecting from a non-existent ID
        res = supabase.table("citizens").select("*").limit(1).execute()
        if res.data:
            print("Columns in 'citizens' table:")
            print(res.data[0].keys())
        else:
            print("Table is empty, trying to get schema information...")
            # We can try to insert a dummy record and see if it fails or what columns it has
            # But that's risky. Let's try to get one record again.
            print("No data found in 'citizens' table.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_columns())
