# my_os — учебная операционная система

Учебная ОС с монолитным ядром на Python 3.10+ и SQLite.
Индивидуальная тема — **управление процессами: планировщик Round Robin
с четырьмя приоритетами и старением (aging)**.

Автор: Харитонов Даниил Сергеевич, группа 3ИП-7-24

## Возможности

- вход/выход пользователей, пароли в виде SHA-256;
- файлы в таблице `files` (создание, чтение, удаление, список);
- процессы: запуск с приоритетом и памятью, таблица `ps`, `kill`;
- такты планировщика `tick N` — видно, кто получает процессор;
- журнал всех системных вызовов в `syscalls_log`.

## Структура

```
my_os/
├── src/
│   ├── config.py      константы (лимиты, квант, пути)
│   ├── db.py          SQLite: соединение и схема
│   ├── auth.py        пароли и права
│   ├── fs.py          файловая система
│   ├── memory.py      учёт памяти
│   ├── scheduler.py   планировщик Round Robin + приоритеты
│   ├── kernel.py      ядро (класс Kernel)
│   ├── syscalls.py    системные вызовы + журнал
│   └── shell.py       командная оболочка
├── tests/             30 модульных тестов unittest
├── docs/              01_OS_Scope_and_NFR.md, 02_OS_Architecture.md, диаграмма
├── db/                os.sqlite создаётся при первом запуске
└── logs/
```

## Запуск

```bash
python src/db.py              # создать базу (необязательно — создаётся сама)
python -m src.syscalls        # самопроверка API
python -m src.shell           # оболочка
python -m unittest discover -s tests -v
```

Учётные записи для демонстрации: `root / root123` (admin),
`student / student1` (user).

## Пример сеанса

```
guest@my_os:~$ login root
  пароль: ********
root@my_os:~$ run compiler 3 512
root@my_os:~$ run backup 0 128
root@my_os:~$ tick 16
  CPU: 1 → 1 → ... → 2 → 2 → 1 → 1
root@my_os:~$ ps
```
