import os
import logging
from sqlalchemy import create_engine
from src.session import DEFAULT_DB_PATH, Base

# Set up logging
logger = logging.getLogger(__name__)

def create_tables():
    """Create all database tables if they don't exist"""
    logger.info("Initializing database tables...")
    
    # Create database URI
    db_uri = f"sqlite:///{DEFAULT_DB_PATH}"
    
    # Create engine and tables
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    
    logger.info("Database tables initialized successfully")

def init_db():
    """Initialize the database"""
    try:
        # Ensure the database directory exists
        db_dir = os.path.dirname(DEFAULT_DB_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"Created database directory: {db_dir}")
            
        create_tables()
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False 