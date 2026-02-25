#!/usr/bin/env python3
"""
Script to apply database migrations to the remote server database.
This script automates the process of connecting to the server database and running migrations.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to Python path
project_root = Path(__file__).parent
print(f"Project root: {project_root}")
sys.path.insert(0, str(project_root))

def check_prerequisites():
    """Check if required tools are available."""
    logger.info("Checking prerequisites...")
    
    # Check if alembic is available
    try:
        import alembic
        logger.info("✓ Alembic is available")
    except ImportError:
        logger.error("✗ Alembic is not available. Please install it: pip install alembic")
        return False
    
    # Check if alembic.ini exists
    alembic_ini = project_root / "alembic.ini"
    if not alembic_ini.exists():
        logger.error(f"✗ alembic.ini not found at {alembic_ini}")
        return False
    logger.info("✓ alembic.ini found")
    
    return True

def get_server_database_url():
    """Get the server database URL from environment."""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        logger.error("Could not find DATABASE_URL in environment variables")
        logger.error("Please set DATABASE_URL environment variable with the server database connection string")
        return None
    
    logger.info(f"✓ Database URL found: {database_url.split('@')[1] if '@' in database_url else '***'}")
    return database_url

def run_migration_command(command, database_url):
    """Run an alembic command with the server database URL."""
    try:
        # Set environment variables
        env = os.environ.copy()
        env['DATABASE_URL'] = database_url
        env['ENV_STAGE'] = 'production'
        
        # Split command into parts for subprocess
        command_parts = command.split()
        
        # Run the command
        result = subprocess.run(
            ['alembic'] + command_parts,
            env=env,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info(f"✓ Command 'alembic {command}' completed successfully")
        if result.stdout:
            logger.info(f"Output: {result.stdout}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Command 'alembic {command}' failed")
        logger.error(f"Error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error running 'alembic {command}': {e}")
        return False

def check_current_revision(database_url):
    """Check the current migration revision in the database."""
    logger.info("Checking current database revision...")
    
    try:
        # Set environment variables
        env = os.environ.copy()
        env['DATABASE_URL'] = database_url
        env['ENV_STAGE'] = 'production'
        
        # Run alembic current
        result = subprocess.run(
            ['alembic', 'current'],
            env=env,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        
        current_revision = result.stdout.strip()
        logger.info(f"✓ Current revision: {current_revision}")
        return current_revision
        
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Failed to get current revision: {e.stderr}")
        return None

def main():
    """Main function to apply migrations to server database."""
    logger.info("🚀 Starting server database migration script...")
    
    # Check prerequisites
    if not check_prerequisites():
        logger.error("❌ Prerequisites check failed. Exiting.")
        sys.exit(1)
    
    # Get database URL
    database_url = get_server_database_url()
    if not database_url:
        logger.error("❌ Could not get database URL. Exiting.")
        sys.exit(1)
    
    # Check current revision
    current_revision = check_current_revision(database_url)
    if current_revision is None:
        logger.error("❌ Could not determine current revision. Exiting.")
        sys.exit(1)
    
    # Check if we need to upgrade
    logger.info("Checking if migrations need to be applied...")
    
    try:
        # Set environment variables
        env = os.environ.copy()
        env['DATABASE_URL'] = database_url
        env['ENV_STAGE'] = 'production'
        
        # Check what migrations are available
        result = subprocess.run(
            ['alembic', 'heads'],
            env=env,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        
        head_revision = result.stdout.strip()
        logger.info(f"✓ Head revision: {head_revision}")
        
        if current_revision == head_revision:
            logger.info("✅ Database is already up to date. No migrations needed.")
            return
        
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Failed to check head revision: {e.stderr}")
        sys.exit(1)
    
    # Apply migrations
    logger.info("🔄 Applying migrations to server database...")
    if run_migration_command('upgrade head', database_url):
        logger.info("✅ Migrations applied successfully!")
        
        # Verify the upgrade
        new_revision = check_current_revision(database_url)
        if new_revision:
            logger.info(f"✅ Database now at revision: {new_revision}")
    else:
        logger.error("❌ Failed to apply migrations.")
        sys.exit(1)

if __name__ == "__main__":
    main()
