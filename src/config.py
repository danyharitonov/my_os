"""Настройки my_os. Все «магические числа» системы собраны здесь."""
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
# Путь к базе можно переопределить переменной окружения (используется в тестах)
DB_FILE = Path(os.environ.get("MY_OS_DB", ROOT_DIR / "db" / "os.sqlite"))
LOG_FILE = ROOT_DIR / "logs" / "kernel.log"

OS_NAME = "my_os"
OS_VERSION = "0.1"
HOST = "my_os"

# Учётные записи, создаваемые при первом запуске: (логин, пароль, роль)
DEFAULT_ACCOUNTS = (
    ("root", "root123", "admin"),
    ("student", "student1", "user"),
)
