import asyncio
from app.config.supabase import supabase

async def check_buckets():
    try:
        res = supabase.storage.list_buckets()
        print("Buckets:")
        for bucket in res:
            print(f"- {bucket.name} (Public: {bucket.public})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_buckets())
