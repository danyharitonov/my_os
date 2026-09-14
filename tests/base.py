"""Общая подготовка: каждый тест получает чистую временную базу."""
import os
import tempfile
import unittest

from src import config, db, kernel


class FreshOS(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        db.close_connection()
        kernel.reset_kernel()
        self._old_db = config.DB_FILE
        config.DB_FILE = type(config.DB_FILE)(os.path.join(self._tmp.name, "test.sqlite"))
        self.k = kernel.get_kernel()

    def tearDown(self):
        db.close_connection()
        kernel.reset_kernel()
        config.DB_FILE = self._old_db
        self._tmp.cleanup()

    def log_rows(self, name=None):
        sql = "SELECT * FROM syscalls_log" + (" WHERE call_name = ?" if name else "")
        return db.get_connection().execute(sql, (name,) if name else ()).fetchall()
