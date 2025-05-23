import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

# Database file path - adjust as needed
DEFAULT_DB_PATH = os.path.join("/data", "database.sqlite")

def _ensure_db_directory(db_path: str) -> None:
    """Ensure the directory for the database file exists"""
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

@contextmanager
def get_session() -> Generator[sqlite3.Connection, None, None]:
    """Get a SQLite database session as a context manager
    
    Args:
        db_path: Path to the SQLite database file
        
    Yields:
        SQLite connection object with dictionary row factory
    """
    _ensure_db_directory(DEFAULT_DB_PATH)
    
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
    
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
