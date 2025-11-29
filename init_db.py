"""
Initialize fresh database with correct schema
"""
from app import app, db
import os

def init_database():
    """Initialize database with fresh schema"""
    
    # Remove old database if exists
    db_path = 'financial_coach.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✓ Removed old database: {db_path}")
    
    # Create new database with correct schema
    with app.app_context():
        # Drop all tables first
        db.drop_all()
        print("✓ Dropped all existing tables")
        
        # Create all tables fresh
        db.create_all()
        print("✓ Created new database with correct schema")
        
        # Verify tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"✓ Created tables: {', '.join(tables)}")
        
        # Verify Task table has parent_task_id
        task_columns = [col['name'] for col in inspector.get_columns('task')]
        if 'parent_task_id' in task_columns:
            print("✓ Task table has parent_task_id column")
        else:
            print("❌ Task table missing parent_task_id column")
        
    print("\n✅ Database initialization complete!")
    print("Run: python sample_data.py")

if __name__ == '__main__':
    init_database()
