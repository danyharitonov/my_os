import time

from src import config
from src import syscalls as sc
from tests.base import FreshOS


class TestProcesses(FreshOS):
    def setUp(self):
        super().setUp()
        sc.sys_login("student", "student1")

    def test_exec_and_ps(self):
        pid = sc.sys_exec("editor", 2, 128)
        procs = sc.sys_ps()
        self.assertEqual(procs[0]["pid"], pid)
        self.assertEqual(procs[0]["state"], "ready")
        self.assertEqual(procs[0]["priority"], 2)

    def test_ten_processes_supported(self):              # NFR-P2
        pids = [sc.sys_exec(f"job{i}", 1, 64) for i in range(config.MAX_PROCESSES)]
        self.assertNotIn(-1, pids)
        self.assertEqual(sc.sys_exec("extra", 1, 64), -1)

    def test_memory_limit(self):                         # NFR-R2
        self.assertEqual(sc.sys_exec("huge", 1, config.MEMORY_LIMIT_KB + 1), -1)
        pid = sc.sys_exec("ok", 1, config.MEMORY_LIMIT_KB - 100)
        self.assertEqual(sc.sys_mem_alloc(200, pid), -1)
        self.assertEqual(sc.sys_mem_alloc(100, pid), config.MEMORY_LIMIT_KB)

    def test_kill_frees_memory(self):
        pid = sc.sys_exec("tmp", 1, 1000)
        self.assertTrue(sc.sys_kill(pid))
        self.assertEqual(sc.sys_ps(), [])
        self.assertNotEqual(sc.sys_exec("big", 1, config.MEMORY_LIMIT_KB), -1)

    def test_user_cannot_kill_foreign(self):
        sc.sys_login("root", "root123")
        pid = sc.sys_exec("daemon", 3, 64)
        sc.sys_login("student", "student1")
        self.assertFalse(sc.sys_kill(pid))

    def test_invalid_priority(self):
        self.assertEqual(sc.sys_exec("bad", 9, 64), -1)


class TestScheduler(FreshOS):
    def setUp(self):
        super().setUp()
        sc.sys_login("root", "root123")

    def test_round_robin_equal_priority(self):
        a, b = sc.sys_exec("a", 1, 64), sc.sys_exec("b", 1, 64)
        self.assertEqual(sc.sys_tick(6), [a, a, b, b, a, a])   # квант = 2 такта

    def test_higher_priority_first(self):
        low = sc.sys_exec("low", 0, 64)
        high = sc.sys_exec("high", 3, 64)
        self.assertEqual(sc.sys_tick(2), [high, high])
        self.assertNotEqual(low, high)

    def test_low_priority_not_starved(self):             # NFR-R3
        low = sc.sys_exec("backup", 0, 64)
        sc.sys_exec("compiler", 3, 64)
        self.assertIn(low, sc.sys_tick(16))

    def test_idle_when_no_processes(self):
        self.assertEqual(sc.sys_tick(2), [None, None])

    def test_shutdown_admin_only(self):
        sc.sys_exec("x", 1, 64)
        sc.sys_login("student", "student1")
        self.assertFalse(sc.sys_shutdown())
        sc.sys_login("root", "root123")
        self.assertTrue(sc.sys_shutdown())
        self.assertEqual(sc.sys_ps(), [])


class TestJournalAndNFR(FreshOS):
    def test_every_call_logged(self):                    # NFR-S3
        before = len(self.log_rows())
        sc.sys_echo("a")
        sc.sys_whoami()
        sc.sys_ps()
        self.assertEqual(len(self.log_rows()), before + 3)

    def test_logs_admin_only(self):
        self.assertEqual(sc.sys_logs(5), [])
        sc.sys_login("root", "root123")
        self.assertGreaterEqual(len(sc.sys_logs(5)), 1)

    def test_syscall_time_budget(self):                  # NFR-P1, NFR-P3
        sc.sys_login("root", "root123")
        for i in range(10):
            sc.sys_exec(f"p{i}", i % 4, 64)
        started = time.perf_counter()
        sc.sys_tick(1)
        self.assertLess((time.perf_counter() - started) * 1000, config.SYSCALL_BUDGET_MS)

    def test_kernel_survives_internal_error(self):       # NFR-R1
        sc.sys_login("root", "root123")
        self.assertEqual(sc.sys_kill("не число"), False)
        self.assertEqual(sc.sys_echo("жив"), "жив")
