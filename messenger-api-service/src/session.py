import os
import sqlite3
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.ext.declarative import declarative_base

# Default database path
DEFAULT_DB_PATH = os.path.join("/database", "telegram_api.db")

# Create Base class for SQLAlchemy models
Base = declarative_base()

def _ensure_db_directory(db_path: str) -> None:
    """Ensure the directory for the database file exists"""
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

@contextmanager
def get_db(db_path: str = DEFAULT_DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Get a SQLite database session as a context manager
    
    Args:
        db_path: Path to the SQLite database file
        
    Yields:
        SQLite connection object with dictionary row factory
    """
    _ensure_db_directory(db_path)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
    
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close() 