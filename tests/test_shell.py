import io
from contextlib import redirect_stdout
from unittest import mock

from src import shell
from tests.base import FreshOS


class TestShell(FreshOS):
    def run_lines(self, *lines, inputs=()):
        out = io.StringIO()
        with redirect_stdout(out), mock.patch("builtins.input", side_effect=list(inputs)):
            for line in lines:
                shell.execute(line)
        return out.getvalue()

    def test_prompt_changes_after_login(self):
        self.assertTrue(shell.prompt().startswith("guest@my_os"))
        self.run_lines("login root", inputs=["root123"])
        self.assertTrue(shell.prompt().startswith("root@my_os"))

    def test_unknown_command(self):
        self.assertIn("не найдена", self.run_lines("format c:"))

    def test_run_and_ps_output(self):
        out = self.run_lines("login student", "run game 2 100", "ps", inputs=["student1"])
        self.assertIn("PID=1", out)
        self.assertIn("game", out)

    def test_non_number_argument(self):
        out = self.run_lines("login root", "kill abc", inputs=["root123"])
        self.assertIn("ожидалось число", out)
