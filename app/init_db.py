from app.database import create_db_and_tables
from app.models import KeyHistory

if __name__ == "__main__":
    create_db_and_tables()
    print("Database initialized.")
