"""Initialize the database with sample data."""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.storage.database import engine


async def init_database():
    """Initialize database with sample data."""
    print("Initializing database...")

    async with engine.begin() as conn:
        # Check if pgvector extension exists
        result = await conn.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        has_vector = result.scalar()

        if not has_vector:
            print("Creating pgvector extension...")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Insert sample customer
        await conn.execute(
            text("""
                INSERT INTO customers (id, name, email, phone)
                VALUES (
                    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
                    'João Silva',
                    'joao.silva@example.com',
                    '+55 11 99999-0000'
                )
                ON CONFLICT (email) DO NOTHING
            """)
        )

        # Insert sample vehicle
        await conn.execute(
            text("""
                INSERT INTO vehicles (id, customer_id, brand, model, year, vin, license_plate)
                VALUES (
                    'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
                    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
                    'Volkswagen',
                    'T-Cross',
                    2023,
                    '9BWZZZ1KZ3P123456',
                    'ABC-1234'
                )
                ON CONFLICT (vin) DO NOTHING
            """)
        )

        # Insert sample service history
        await conn.execute(
            text("""
                INSERT INTO service_history (vehicle_id, service_type, description, service_date, mileage, cost)
                VALUES (
                    'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22',
                    'Oil Change',
                    'Synthetic oil change with filter replacement',
                    '2024-01-15',
                    15000,
                    89.99
                )
                ON CONFLICT DO NOTHING
            """)
        )

    print("Database initialized successfully!")
    print("Sample data:")
    print("- Customer: João Silva (joao.silva@example.com)")
    print("- Vehicle: Volkswagen T-Cross 2023")
    print("- Service: Oil Change on 2024-01-15")


if __name__ == "__main__":
    asyncio.run(init_database())
