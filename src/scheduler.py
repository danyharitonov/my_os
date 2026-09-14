"""Планировщик my_os: Round Robin с четырьмя уровнями приоритета и старением.

Очереди хранятся в памяти (по одной deque на приоритет), а состояние каждого
процесса дублируется в таблице processes (риск R7).
"""
from collections import deque

from src import config
from src.db import get_connection


class Scheduler:
    def __init__(self):
        self.queues = [deque() for _ in range(config.PRIORITY_LEVELS)]
        self.waiting_since = {}   # pid -> тактов без процессора (для старения)
        self.current = None       # pid, занимающий процессор
        self.slice_left = 0
        self.restore()

    # ---------- работа с таблицей ----------
    def _set_state(self, pid, state):
        conn = get_connection()
        conn.execute("UPDATE processes SET state = ? WHERE pid = ?", (state, pid))
        conn.commit()

    def restore(self):
        """Восстанавливает очереди из БД после перезапуска."""
        rows = get_connection().execute(
            "SELECT pid, priority FROM processes WHERE state IN ('ready', 'running') ORDER BY pid")
        for row in rows:
            self._enqueue(row["pid"], row["priority"])
            self._set_state(row["pid"], "ready")

    def active_count(self):
        return get_connection().execute(
            "SELECT COUNT(*) FROM processes WHERE state != 'terminated'").fetchone()[0]

    # ---------- очереди ----------
    def _enqueue(self, pid, priority):
        priority = max(0, min(priority, config.PRIORITY_LEVELS - 1))
        self.queues[priority].append(pid)
        self.waiting_since[pid] = 0

    def admit(self, name, owner, priority, memory_kb):
        conn = get_connection()
        cur = conn.execute(
            "INSERT INTO processes(name, state, owner, memory_kb, priority) VALUES (?, 'new', ?, ?, ?)",
            (name, owner, memory_kb, priority))
        conn.commit()
        pid = cur.lastrowid
        self._enqueue(pid, priority)
        self._set_state(pid, "ready")
        return pid

    def drop(self, pid):
        for q in self.queues:
            if pid in q:
                q.remove(pid)
        self.waiting_since.pop(pid, None)
        if self.current == pid:
            self.current, self.slice_left = None, 0
        self._set_state(pid, "terminated")

    def _pick(self):
        for level in range(config.PRIORITY_LEVELS - 1, -1, -1):
            if self.queues[level]:
                return self.queues[level].popleft(), level
        return None, None

    def _age(self):
        """Ожидающие слишком долго поднимаются на уровень выше (R6, NFR-R3)."""
        for level in range(config.PRIORITY_LEVELS - 1):
            for pid in list(self.queues[level]):
                self.waiting_since[pid] += 1
                if self.waiting_since[pid] >= config.AGING_TICKS:
                    self.queues[level].remove(pid)
                    self.queues[level + 1].append(pid)
                    self.waiting_since[pid] = 0
        for pid in self.queues[-1]:
            self.waiting_since[pid] += 1

    def tick(self):
        """Один такт таймера. Возвращает PID, получивший процессор, или None."""
        if self.current is None or self.slice_left == 0:
            if self.current is not None:          # квант исчерпан — в конец очереди
                prio = self._priority(self.current)
                self._set_state(self.current, "ready")
                self._enqueue(self.current, prio)
            self.current, _ = self._pick()
            self.slice_left = config.QUANTUM_TICKS
            if self.current is None:
                return None
            self._set_state(self.current, "running")
        self._age()
        conn = get_connection()
        conn.execute("UPDATE processes SET cpu_ticks = cpu_ticks + 1 WHERE pid = ?", (self.current,))
        conn.commit()
        self.slice_left -= 1
        return self.current

    def _priority(self, pid):
        row = get_connection().execute("SELECT priority FROM processes WHERE pid = ?", (pid,)).fetchone()
        return row["priority"] if row else 0

    def snapshot(self):
        rows = get_connection().execute(
            "SELECT pid, name, state, owner, priority, memory_kb, cpu_ticks FROM processes "
            "WHERE state != 'terminated' ORDER BY pid")
        return [dict(r) for r in rows]
