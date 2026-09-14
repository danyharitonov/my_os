from src import db
from tests.base import FreshOS
from src import syscalls as sc


class TestStorage(FreshOS):
    def test_four_tables_created(self):
        names = {r[0] for r in db.get_connection().execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"users", "processes", "files", "syscalls_log"} <= names)

    def test_init_is_idempotent(self):
        db.init_db()
        db.init_db()
        count = db.get_connection().execute("SELECT COUNT(*) FROM users").fetchone()[0]
        self.assertEqual(count, 2)

    def test_passwords_stored_as_sha256(self):           # NFR-S1
        for row in db.get_connection().execute("SELECT pwd_hash FROM users"):
            self.assertEqual(len(row[0]), 64)
            self.assertNotIn("root123", row[0])


class TestLogin(FreshOS):
    def test_good_and_bad_password(self):
        self.assertFalse(sc.sys_login("root", "wrong"))
        self.assertEqual(sc.sys_whoami(), "guest")
        self.assertTrue(sc.sys_login("root", "root123"))
        self.assertEqual(sc.sys_whoami(), "root")

    def test_password_hidden_in_log(self):              # NFR-S4
        sc.sys_login("student", "student1")
        args = self.log_rows("sys_login")[-1]["args"]
        self.assertIn("***", args)
        self.assertNotIn("student1", args)

    def test_logout_returns_to_guest(self):
        sc.sys_login("student", "student1")
        self.assertTrue(sc.sys_logout())
        self.assertEqual(sc.sys_whoami(), "guest")
        self.assertFalse(sc.sys_logout())
