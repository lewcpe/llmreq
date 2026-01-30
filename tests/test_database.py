from app.database import get_session, create_db_and_tables

def test_get_session():
    gen = get_session()
    session = next(gen)
    assert session
    gen.close()

def test_create_db_and_tables():
    # This might fail if using real DB file?
    # But database.py uses "sqlite:///./app.db" by default from config.
    # We can patch config or just run it.
    create_db_and_tables()
