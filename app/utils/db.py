"""
Database Utility Module

Provides a helper function to connect to the MariaDB database using environment variables.
"""

import os
import mysql.connector
from mysql.connector.connection import MySQLConnection


def ensure_schema() -> None:
    """Applies any missing schema migrations (idempotent)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "ALTER TABLE sites "
        "ADD COLUMN IF NOT EXISTS system_type VARCHAR(50) NOT NULL DEFAULT 'momentum'"
    )
    cursor.execute(
        "ALTER TABLE sites MODIFY COLUMN base_url VARCHAR(500) NULL DEFAULT NULL"
    )
    cursor.execute(
        "ALTER TABLE sites "
        "ADD COLUMN IF NOT EXISTS momentum_id VARCHAR(100) DEFAULT NULL"
    )
    cursor.execute(
        "ALTER TABLE sites DROP COLUMN IF EXISTS return_address"
    )
    cursor.execute(
        "ALTER TABLE sites DROP COLUMN IF EXISTS api_key"
    )
    cursor.execute(
        "ALTER TABLE sites DROP COLUMN IF EXISTS momentum_site_id"
    )
    cursor.execute(
        "ALTER TABLE sites DROP COLUMN IF EXISTS momentum_cname"
    )
    cursor.execute(
        "ALTER TABLE credentials "
        "ADD COLUMN IF NOT EXISTS queue_points INT DEFAULT NULL"
    )
    cursor.execute(
        "ALTER TABLE credentials "
        "ADD COLUMN IF NOT EXISTS queue_details TEXT DEFAULT NULL"
    )
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            `key` VARCHAR(100) PRIMARY KEY,
            `value` TEXT NOT NULL
        )
    """)
    cursor.execute(
        "INSERT IGNORE INTO settings (`key`, `value`) VALUES ('momentum_api_key', '')"
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_setting(key: str) -> str:
    """Returns the value for a global setting key, or '' if not set."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT `value` FROM settings WHERE `key` = %s", (key,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else ""


def get_connection() -> MySQLConnection:
    """
    Establishes a connection to the MariaDB database using environment variables.

    Returns:
        MySQLConnection: A live connection to the database.

    Raises:
        KeyError: If any required environment variable is missing.
        mysql.connector.Error: If the connection fails.
    """
    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        database=os.environ["DB_NAME"]
    )
