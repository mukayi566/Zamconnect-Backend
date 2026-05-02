import asyncio
from app.config.supabase import supabase

async def create_citizens_bucket():
    try:
        # Check if it exists first
        buckets = supabase.storage.list_buckets()
        exists = any(b.name == 'citizens' for b in buckets)
        
        if not exists:
            print("Creating 'citizens' bucket...")
            supabase.storage.create_bucket('citizens', options={'public': True})
            print("'citizens' bucket created successfully.")
        else:
            print("'citizens' bucket already exists.")
            # Ensure it is public
            for b in buckets:
                if b.name == 'citizens' and not b.public:
                    print("Updating 'citizens' bucket to be public...")
                    supabase.storage.update_bucket('citizens', options={'public': True})
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(create_citizens_bucket())
