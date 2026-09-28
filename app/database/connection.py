from contextlib import contextmanager
from typing import Generator

import mysql.connector
from mysql.connector import MySQLConnection

from app.config.settings import get_settings


@contextmanager
def get_db_connection() -> Generator[MySQLConnection, None, None]:
    """
    Create a MySQL database connection and automatically
    close it when the operation is complete.
    """

    settings = get_settings()

    connection = mysql.connector.connect(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )

    try:
        yield connection
    finally:
        if connection.is_connected():
            connection.close()


def test_database_connection() -> bool:
    """
    Test whether the application can successfully connect
    to the configured MySQL database.
    """

    try:
        with get_db_connection() as connection:
            return connection.is_connected()

    except mysql.connector.Error as error:
        print(f"Database connection failed: {error}")
        return False