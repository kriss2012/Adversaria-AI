import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

async def test():
    try:
        engine = create_async_engine(os.getenv('DATABASE_URL'))
        async with engine.connect() as conn:
            print("Connected successfully to DB!")
    except Exception as e:
        print("Failed to connect:", e)

if __name__ == "__main__":
    asyncio.run(test())
