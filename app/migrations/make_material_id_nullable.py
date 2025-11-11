"""
Database migration: Make material_id nullable in ar_tags table
"""
from sqlalchemy import create_engine, text
from app.database import get_database_url

def migrate():
    """Make material_id nullable in ar_tags table"""
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        try:
            # Make material_id nullable
            conn.execute(text("""
                ALTER TABLE ar_tags
                ALTER COLUMN material_id DROP NOT NULL
            """))
            conn.commit()
            print("✅ Migration completed: material_id is now nullable in ar_tags table")
        except Exception as e:
            print(f"⚠️ Migration note: {e}")
            print("This might be okay if the column is already nullable")
            conn.rollback()

if __name__ == "__main__":
    migrate()
