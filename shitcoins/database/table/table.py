from __future__ import annotations

import logging
from typing import List

import psycopg2.errors
import psycopg2

LOGGER = logging.getLogger(__name__)


class Table:
    def __init__(self, cursor):
        self._cursor = cursor

    def _create_table(self, table_name: str, variables: str):
        """
        Creates table in postgres database
        :param table_name: name of table
        :param variables: the column names and types
        """
        self._cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({variables})")

    def _create_enum(self, enum_name: str, values: str):
        """
        Creates enum type in postgres database
        :param enum_name: enum name
        :param values: enum values
        """
        self._cursor.execute(f"DROP TYPE IF EXISTS {enum_name} CASCADE")
        self._cursor.execute(f"CREATE TYPE {enum_name} AS ENUM ({values})")

    def _truncate_table(self, table_name: str):
        """
        Truncates table in postgres database
        :param table_name: name of table
        """
        self._cursor.execute(f"TRUNCATE {table_name}")

    def _insert_entry(self, table_name: str, entry: str):
        try:
            self._cursor.execute(f"INSERT INTO {table_name} VALUES {entry} ")
        except psycopg2.errors.lookup("23505"):
            LOGGER.error(f"UniqueViolation: Insertion of PK with non unique address {entry}")

    def _insert_entry_if_not_exist(self, table_name: str, entry: str):
        self._cursor.execute(f"INSERT INTO {table_name} VALUES {entry} "
                             f"ON CONFLICT DO NOTHING")

    def _get_entries(self, table_name: str) -> List:
        """
        Selects all entry from the table
        :param table_name: name of table
        """
        self._cursor.execute(f"SELECT * FROM {table_name}")
        return self._cursor.fetchall()

    def _get_entry_by_key(self, table_name: str, key_name: str, key_value: str | int):
        """
        Selects entry from a particular column of the table
        :param table_name: name of table
        :param key_name: name of key to be used
        :param key_value: desired value of key
        """
        try:
            if isinstance(key_value, str):
                self._cursor.execute(f"SELECT * FROM {table_name} WHERE {key_name}='{key_value}'")
            else:
                self._cursor.execute(f"SELECT * FROM {table_name} WHERE {key_name}={key_value}")
        except psycopg2.Error:
            return None
        return self._cursor.fetchone()

    def _get_entries_by_key(self, table_name: str, key_name: str, key_value: any):
        """
        Selects entries from a particular column of the table
        :param table_name: name of table
        :param key_name: name of key to be used
        :param key_value: desired value of key
        """
        try:
            self._cursor.execute(f"SELECT * FROM {table_name} WHERE {key_name}={key_value}")
        except psycopg2.Error:
            return None
        return self._cursor.fetchall()

    def _get_entries_by_key_to_multiple_values(self, table_name: str, key_name: str, key_value: List[any]):
        """
        Selects all entries from a particular column of the table
        :param table_name: name of table
        :param key_name: name of key to be used
        :param key_value: desired list of values that match the key-value
        """
        try:
            self._cursor.execute(f"SELECT * FROM {table_name} WHERE ANY({key_name}={key_value})")
        except psycopg2.Error:
            return None
        return self._cursor.fetchall()

    def _update_table(self, table_name: str, update_statement: str):
        """
        updates values of table
        :param table_name name of table
        :param update_statement: the variable to be updated i.e. "status = 'OLD' WHERE address = 'abc'"
        """
        self._cursor.execute(f"UPDATE {table_name} SET {update_statement}")
