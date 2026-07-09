import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

# Explicitly load the .env file in the current directory
env_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
print("Loading dotenv from:", env_path)
load_dotenv(env_path)

async def test():
    db_url = os.getenv('DATABASE_URL')
    print("DATABASE_URL:", db_url)
    try:
        engine = create_async_engine(db_url)
        async with engine.connect() as conn:
            print("Connected successfully to DB!")
    except Exception as e:
        print("Failed to connect:", e)

if __name__ == "__main__":
    asyncio.run(test())
