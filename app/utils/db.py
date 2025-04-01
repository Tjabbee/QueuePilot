"""
Database Utility Module

Provides a helper function to connect to the MariaDB database using environment variables.
"""

import os
import mysql.connector
from mysql.connector.connection import MySQLConnection


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
