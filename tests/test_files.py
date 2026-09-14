from src import syscalls as sc
from tests.base import FreshOS


class TestFiles(FreshOS):
    def test_guest_cannot_create(self):
        self.assertEqual(sc.sys_create_file("/home/guest/a.txt", "x"), -1)
        self.assertIn("вход", sc.last_error)

    def test_create_read_list_delete(self):
        sc.sys_login("student", "student1")
        fid = sc.sys_create_file("/home/student/notes.txt", "квант")
        self.assertGreater(fid, 0)
        self.assertEqual(sc.sys_read_file("/home/student/notes.txt"), "квант")
        self.assertEqual(sc.sys_list_files("/home/student"), ["/home/student/notes.txt"])
        self.assertTrue(sc.sys_delete_file("/home/student/notes.txt"))
        self.assertEqual(sc.sys_list_files("/home/student"), [])

    def test_user_limited_to_own_home(self):
        sc.sys_login("student", "student1")
        self.assertEqual(sc.sys_create_file("/home/root/x.txt", "x"), -1)

    def test_user_cannot_delete_admin_file(self):          # NFR-S2
        sc.sys_login("root", "root123")
        sc.sys_create_file("/home/root/secret.txt", "s")
        sc.sys_login("student", "student1")
        self.assertFalse(sc.sys_delete_file("/home/root/secret.txt"))
        self.assertEqual(self.log_rows("sys_delete_file")[-1]["status"], "denied")

    def test_duplicate_path_rejected(self):
        sc.sys_login("student", "student1")
        sc.sys_create_file("/home/student/a", "1")
        self.assertEqual(sc.sys_create_file("/home/student/a", "2"), -1)
