"""Safely apply the Domain v2 migration to the configured core database.

The project's MySQL version does not support ``ADD COLUMN IF NOT EXISTS``.
This runner checks each target column first, then applies only missing changes.
It is safe to re-run because the seed inserts in migration_v2.sql use INSERT IGNORE.
"""
from pathlib import Path
import re
import sys

import pymysql

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from config import Config


MIGRATION_PATH = BACKEND_DIR / 'sql' / 'migration_v2.sql'
ALTER_COLUMN_PATTERN = re.compile(
    r'ALTER TABLE `(?P<table>[^`]+)` ADD COLUMN IF NOT EXISTS `(?P<column>[^`]+)`',
    re.IGNORECASE,
)


def column_exists(cursor, table_name, column_name):
    """Return whether a column is already present in the configured database."""
    cursor.execute(
        '''
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        ''',
        (Config.MYSQL_DB, table_name, column_name),
    )
    return cursor.fetchone() is not None


def ensure_grayscale_unique_key(cursor):
    """Keep the oldest config for each key and enforce the migration's unique key."""
    cursor.execute(
        '''
        DELETE duplicate_row
        FROM grayscale_config AS duplicate_row
        INNER JOIN grayscale_config AS retained_row
          ON duplicate_row.config_key = retained_row.config_key
         AND duplicate_row.domain = retained_row.domain
         AND duplicate_row.id > retained_row.id
        '''
    )
    print(f'cleaned duplicate grayscale rows: {cursor.rowcount}')

    cursor.execute(
        '''
        SELECT 1
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'grayscale_config'
          AND INDEX_NAME = 'uk_key_domain'
        ''',
        (Config.MYSQL_DB,),
    )
    if cursor.fetchone() is None:
        cursor.execute(
            'ALTER TABLE grayscale_config ADD UNIQUE KEY uk_key_domain (config_key, domain)'
        )
        print('created grayscale_config.uk_key_domain')


def main():
    statements = MIGRATION_PATH.read_text(encoding='utf-8-sig').split(';')
    connection = pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        charset='utf8mb4',
    )

    try:
        with connection.cursor() as cursor:
            for index, statement in enumerate(statements, start=1):
                statement = statement.strip()
                if not statement:
                    continue

                # Statements 1-5 establish the table and its columns. Enforce
                # the unique key before statement 6 starts inserting seed data.
                if index == 6:
                    ensure_grayscale_unique_key(cursor)

                alter_match = ALTER_COLUMN_PATTERN.search(statement)
                if alter_match:
                    table_name = alter_match.group('table')
                    column_name = alter_match.group('column')
                    if column_exists(cursor, table_name, column_name):
                        print(f'[{index}] skipped: {table_name}.{column_name} already exists')
                        continue
                    statement = statement.replace(' IF NOT EXISTS', '')

                cursor.execute(statement)
                print(f'[{index}] affected rows: {cursor.rowcount}')

        connection.commit()
        print('Migration v2 applied successfully.')
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    main()
