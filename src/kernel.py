"""Ядро my_os. Хранит сеанс, проверяет права и вызывает подсистемы.

Оболочка не видит этот модуль: она обращается только к syscalls.py.
"""
from src import auth, config, fs, memory
from src.db import get_connection, init_db
from src.scheduler import Scheduler


class KernelError(Exception):
    """Отказ ядра в выполнении операции (нет прав, нет ресурса)."""


class Kernel:
    def __init__(self):
        init_db()
        self.user = "guest"
        self.role = None
        self.running = True
        self.scheduler = Scheduler()

    # ----- сеанс -----
    def login(self, login, password):
        role = auth.check_credentials(login, password)
        if role is None:
            return False
        self.user, self.role = login, role
        return True

    def logout(self):
        was = self.role is not None
        self.user, self.role = "guest", None
        return was

    def require_login(self):
        if self.role is None:
            raise KernelError("требуется вход в систему")

    def require_admin(self):
        if self.role != "admin":
            raise KernelError("операция только для администратора")

    # ----- файлы -----
    def create_file(self, path, content):
        self.require_login()
        if self.role != "admin" and not path.startswith(f"/home/{self.user}/"):
            raise KernelError("можно создавать файлы только в своём каталоге")
        if fs.stat(path):
            raise KernelError("файл уже существует")
        return fs.create(path, content, self.user)

    def read_file(self, path):
        self.require_login()
        content = fs.read(path)
        if content is None:
            raise KernelError("файл не найден")
        return content

    def delete_file(self, path):
        self.require_login()
        info = fs.stat(path)
        if info is None:
            raise KernelError("файл не найден")
        if not auth.may_modify(self.user, self.role, info["owner"]):
            raise KernelError("нельзя удалить чужой файл")
        return fs.remove(path)

    def list_files(self, path):
        self.require_login()
        return fs.listdir(path)

    # ----- процессы и память -----
    def exec(self, name, priority, memory_kb):
        self.require_login()
        if not 0 <= priority < config.PRIORITY_LEVELS:
            raise KernelError("приоритет должен быть от 0 до 3")
        if self.scheduler.active_count() >= config.MAX_PROCESSES:
            raise KernelError("достигнут лимит процессов")
        if not memory.can_allocate(memory_kb):
            raise KernelError("недостаточно памяти")
        return self.scheduler.admit(name, self.user, priority, memory_kb)

    def _process(self, pid):
        row = get_connection().execute(
            "SELECT * FROM processes WHERE pid = ? AND state != 'terminated'", (pid,)).fetchone()
        if row is None:
            raise KernelError(f"процесс {pid} не найден")
        return dict(row)

    def kill(self, pid):
        self.require_login()
        proc = self._process(pid)
        if not auth.may_modify(self.user, self.role, proc["owner"]):
            raise KernelError("нельзя завершить чужой процесс")
        memory.release(pid)
        self.scheduler.drop(pid)
        return True

    def mem_alloc(self, size, pid=None):
        self.require_login()
        if pid is None:
            own = [p for p in self.scheduler.snapshot() if p["owner"] == self.user]
            if not own:
                raise KernelError("нет процесса, которому выделять память")
            pid = own[-1]["pid"]
        self._process(pid)
        return memory.grow(pid, size)

    def ps(self):
        return self.scheduler.snapshot()

    def tick(self, count):
        return [self.scheduler.tick() for _ in range(count)]

    def logs(self, limit):
        self.require_admin()
        rows = get_connection().execute(
            "SELECT id, call_name, args, user, status, ts FROM syscalls_log ORDER BY id DESC LIMIT ?",
            (limit,))
        return [dict(r) for r in rows]

    def shutdown(self):
        self.require_admin()
        for proc in self.scheduler.snapshot():
            memory.release(proc["pid"])
            self.scheduler.drop(proc["pid"])
        self.running = False
        return True

    def users(self):
        return [{"login": u["login"], "role": u["role"]} for u in auth.list_users()]


_kernel = None


def get_kernel():
    """Ядро создаётся один раз на процесс (как при загрузке ОС)."""
    global _kernel
    if _kernel is None:
        _kernel = Kernel()
    return _kernel


def reset_kernel():
    global _kernel
    _kernel = None
