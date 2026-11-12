"""Tests for the watch mode (src/watch_mode.py)."""

import logging
import os
import subprocess
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import watch_mode
from watch_mode import (
    TIMEOUT_EXIT_CODE,
    build_child_argv,
    load_secret_env,
    parse_cycle_timeout,
    parse_watch_args,
    run_child,
    watch_loop,
)

LOGGER = logging.getLogger("test-watch")


class CountingStop:
    """Stop signal that stops after a number of waits and records the waited seconds."""

    def __init__(self, stop_after):
        self.stop_after = stop_after
        self.waits = []

    def is_set(self):
        return len(self.waits) >= self.stop_after

    def wait(self, timeout=None):
        self.waits.append(timeout)
        return self.is_set()


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


class TestLoadSecretEnv:
    def test_reads_the_admin_passwords_without_the_trailing_newline(self, tmp_path):
        write(
            tmp_path / "harbor-admin-credentials" / "harbor-admin-password-new",
            "new-pw\n",
        )
        write(
            tmp_path / "harbor-admin-credentials" / "harbor-admin-password-old",
            "old-pw\n\n",
        )

        env = load_secret_env(tmp_path)

        assert env == {"ADMIN_PASSWORD_NEW": "new-pw", "ADMIN_PASSWORD_OLD": "old-pw"}

    def test_keeps_carriage_returns_inside_and_at_the_end_of_a_secret(self, tmp_path):
        path = tmp_path / "harbor-admin-credentials" / "harbor-admin-password-new"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"pass\rword\r\n")

        assert load_secret_env(tmp_path)["ADMIN_PASSWORD_NEW"] == "pass\rword\r"

    def test_every_key_of_the_token_secrets_becomes_a_variable(self, tmp_path):
        write(tmp_path / "harbor-robot-tokens" / "ROBOT_TOKEN_A", "token-a")
        write(tmp_path / "harbor-robot-tokens" / "ROBOT_TOKEN_B", "token-b\n")
        write(
            tmp_path / "oidc-static-client-token" / "OIDC_STATIC_CLIENT_TOKEN", "oidc"
        )

        env = load_secret_env(tmp_path)

        assert env == {
            "ROBOT_TOKEN_A": "token-a",
            "ROBOT_TOKEN_B": "token-b",
            "OIDC_STATIC_CLIENT_TOKEN": "oidc",
        }

    def test_skips_names_that_are_no_variable_names_and_directories(self, tmp_path):
        folder = tmp_path / "harbor-robot-tokens"
        write(folder / "GOOD_NAME", "ok")
        write(folder / "1STARTS_WITH_DIGIT", "no")
        write(folder / "has-dash", "no")
        write(folder / "..data" / "GOOD_NAME", "hidden volume directory")
        write(folder / ".hidden", "no")

        assert load_secret_env(tmp_path) == {"GOOD_NAME": "ok"}

    def test_follows_symlinks_like_a_kubernetes_secret_volume(self, tmp_path):
        folder = tmp_path / "harbor-robot-tokens"
        write(folder / "..2026_11_12" / "TOKEN", "linked")
        (folder / "..data").symlink_to("..2026_11_12")
        (folder / "TOKEN").symlink_to("..data/TOKEN")

        assert load_secret_env(tmp_path) == {"TOKEN": "linked"}

    def test_missing_directories_and_files_provide_nothing(self, tmp_path):
        assert load_secret_env(tmp_path) == {}
        assert load_secret_env(tmp_path / "does-not-exist") == {}

    def test_reads_a_refreshed_secret_on_the_next_call(self, tmp_path):
        path = tmp_path / "harbor-admin-credentials" / "harbor-admin-password-new"
        write(path, "first")
        assert load_secret_env(tmp_path)["ADMIN_PASSWORD_NEW"] == "first"

        write(path, "second")

        assert load_secret_env(tmp_path)["ADMIN_PASSWORD_NEW"] == "second"


class TestParseWatchArgs:
    def test_no_watch_flag_means_a_single_run(self):
        assert parse_watch_args([], {}) is None
        assert parse_watch_args(["--version"], {"WATCH_INTERVAL": "5"}) is None

    def test_default_interval_is_60_seconds(self):
        assert parse_watch_args(["--watch"], {}) == 60

    def test_interval_from_the_argument(self):
        assert parse_watch_args(["--watch", "15"], {"WATCH_INTERVAL": "5"}) == 15

    def test_interval_from_the_environment(self):
        assert parse_watch_args(["--watch"], {"WATCH_INTERVAL": "30"}) == 30

    @pytest.mark.parametrize("value", ["0", "-5", "abc", "1.5"])
    def test_rejects_an_invalid_interval(self, value):
        with pytest.raises(ValueError):
            parse_watch_args(["--watch", value], {})


class TestWatchLoop:
    def test_runs_every_cycle_and_waits_the_interval_between_them(self):
        stop = CountingStop(stop_after=3)
        calls = []

        watch_loop(lambda: calls.append(1) or 0, 42, stop, LOGGER)

        assert len(calls) == 3
        assert stop.waits == [42, 42, 42]

    def test_continues_after_a_failed_cycle_and_logs_it(self, caplog):
        stop = CountingStop(stop_after=3)
        results = iter([3, 0, 1])

        with caplog.at_level(logging.ERROR, logger="test-watch"):
            watch_loop(lambda: next(results), 1, stop, LOGGER)

        failed = [
            r
            for r in caplog.records
            if r.getMessage().startswith("Synchronization cycle failed")
        ]
        assert [r.exit_code for r in failed] == [3, 1]
        # the text log format ignores the extra fields, so the exit code is in the message as well
        assert [r.getMessage() for r in failed] == [
            "Synchronization cycle failed (exit code 3)",
            "Synchronization cycle failed (exit code 1)",
        ]
        assert len(stop.waits) == 3

    def test_continues_after_an_exception(self, caplog):
        stop = CountingStop(stop_after=2)
        calls = []

        def broken():
            calls.append(1)
            raise OSError("cannot read the secret")

        with caplog.at_level(logging.ERROR, logger="test-watch"):
            watch_loop(broken, 1, stop, LOGGER)

        assert len(calls) == 2
        assert any(
            r.getMessage()
            == "Synchronization cycle could not run: cannot read the secret"
            for r in caplog.records
        )

    def test_does_not_run_when_already_stopped(self):
        stop = CountingStop(stop_after=0)
        calls = []

        watch_loop(lambda: calls.append(1) or 0, 1, stop, LOGGER)

        assert calls == []

    def test_does_not_log_a_failure_of_the_cycle_that_was_stopped(self, caplog):
        class StopsDuringTheCycle:
            def __init__(self):
                self.stopped = False

            def is_set(self):
                return self.stopped

            def wait(self, timeout=None):
                return self.stopped

        stop = StopsDuringTheCycle()

        def cycle():
            stop.stopped = (
                True  # SIGTERM arrives while the child runs; the child is terminated
            )
            return TIMEOUT_EXIT_CODE

        with caplog.at_level(logging.ERROR, logger="test-watch"):
            watch_loop(cycle, 1, stop, LOGGER)

        assert not caplog.records


def process_is_gone(pid):
    """True when the process does not exist or is only a zombie that nobody has collected yet."""
    try:
        with open(f"/proc/{pid}/stat") as stat:
            return stat.read().rsplit(")", 1)[1].split()[0] == "Z"
    except FileNotFoundError:
        return True


class TestRunChild:
    def test_returns_the_exit_code(self):
        stop = threading.Event()

        assert (
            run_child(
                [sys.executable, "-c", "import sys; sys.exit(0)"], os.environ, 30, stop
            )
            == 0
        )
        assert (
            run_child(
                [sys.executable, "-c", "import sys; sys.exit(3)"], os.environ, 30, stop
            )
            == 3
        )

    def test_passes_the_environment_to_the_child(self):
        code = "import os, sys; sys.exit(0 if os.environ.get('ADMIN_PASSWORD_NEW') == 'secret' else 1)"
        env = {**os.environ, "ADMIN_PASSWORD_NEW": "secret"}

        assert run_child([sys.executable, "-c", code], env, 30, threading.Event()) == 0

    def test_terminates_a_cycle_that_runs_too_long(self, monkeypatch):
        monkeypatch.setattr(watch_mode, "POLL_SECONDS", 0.1)
        started = time.monotonic()

        code = run_child(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            os.environ,
            1,
            threading.Event(),
        )

        assert code == TIMEOUT_EXIT_CODE
        assert time.monotonic() - started < 15

    def test_terminates_the_child_when_the_loop_is_stopped(self, monkeypatch):
        monkeypatch.setattr(watch_mode, "POLL_SECONDS", 0.1)
        stop = threading.Event()
        threading.Timer(0.5, stop.set).start()
        started = time.monotonic()

        code = run_child(
            [sys.executable, "-c", "import time; time.sleep(60)"], os.environ, 600, stop
        )

        assert code == TIMEOUT_EXIT_CODE
        assert time.monotonic() - started < 15


class TestBuildChildArgv:
    def test_a_frozen_executable_starts_itself(self):
        assert build_child_argv(
            True, "src.harbor", "/app/harbor.py", "/usr/bin/harbor"
        ) == ["/usr/bin/harbor"]

    def test_a_module_is_started_as_a_module(self):
        assert build_child_argv(
            False, "src.harbor", "/repo/src/harbor.py", "/usr/bin/python3"
        ) == [
            "/usr/bin/python3",
            "-m",
            "src.harbor",
        ]

    def test_a_file_is_run_again_as_a_file(self):
        assert build_child_argv(
            False, None, "/repo/src/harbor.py", "/usr/bin/python3"
        ) == [
            "/usr/bin/python3",
            "/repo/src/harbor.py",
        ]

    def test_the_module_child_keeps_the_package_imports_working(self, tmp_path):
        """With the project root only in the working directory, `python -m` finds the package, running the file does not."""
        package = tmp_path / "pkg"
        package.mkdir()
        (package / "__init__.py").write_text("")
        (package / "helper.py").write_text("VALUE = 1\n")
        (package / "main.py").write_text(
            "from pkg.helper import VALUE\nraise SystemExit(0 if VALUE == 1 else 1)\n"
        )
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        as_module = build_child_argv(
            False, "pkg.main", str(package / "main.py"), sys.executable
        )
        as_file = build_child_argv(
            False, None, str(package / "main.py"), sys.executable
        )

        by_module = subprocess.run(
            as_module, cwd=tmp_path, env=env, check=False, capture_output=True
        )
        by_file = subprocess.run(
            as_file, cwd=tmp_path, env=env, check=False, capture_output=True
        )

        assert by_module.returncode == 0
        assert by_file.returncode != 0
        assert b"No module named 'pkg'" in by_file.stderr


class TestParseCycleTimeout:
    def test_default_is_900_seconds(self):
        assert parse_cycle_timeout({}) == 900

    def test_accepts_a_positive_number(self):
        assert parse_cycle_timeout({"CYCLE_TIMEOUT": "30"}) == 30
        assert parse_cycle_timeout({"CYCLE_TIMEOUT": "0.5"}) == 0.5

    @pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf", "abc", ""])
    def test_rejects_a_value_that_would_disable_or_break_the_timeout(self, value):
        with pytest.raises(ValueError):
            parse_cycle_timeout({"CYCLE_TIMEOUT": value})


class TestProcessGroup:
    def test_a_timeout_also_ends_the_processes_that_the_child_started(
        self, tmp_path, monkeypatch
    ):
        """A frozen onefile executable is a bootloader with a worker below it: both have to end."""
        monkeypatch.setattr(watch_mode, "POLL_SECONDS", 0.1)
        monkeypatch.setattr(watch_mode, "TERMINATE_GRACE_SECONDS", 1)
        pid_file = tmp_path / "worker.pid"
        # the "worker" ignores SIGTERM, only SIGKILL of its group ends it; the parent writes its pid and waits
        code = (
            "import signal, subprocess, sys, time\n"
            "worker = subprocess.Popen([sys.executable, '-c', "
            "'import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'])\n"
            f"open({str(pid_file)!r}, 'w').write(str(worker.pid))\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "time.sleep(60)\n"
        )

        result = run_child(
            [sys.executable, "-c", code], os.environ, 2, threading.Event()
        )

        assert result == TIMEOUT_EXIT_CODE
        worker_pid = int(pid_file.read_text())
        deadline = time.monotonic() + 5
        while not process_is_gone(worker_pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        assert process_is_gone(worker_pid)

    def test_a_worker_that_outlives_the_first_process_is_ended_with_the_cycle(
        self, tmp_path
    ):
        pid_file = tmp_path / "worker.pid"
        code = (
            "import subprocess, sys\n"
            "worker = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
            f"open({str(pid_file)!r}, 'w').write(str(worker.pid))\n"
        )

        result = run_child(
            [sys.executable, "-c", code], os.environ, 30, threading.Event()
        )

        assert result == 0
        worker_pid = int(pid_file.read_text())
        deadline = time.monotonic() + 5
        while not process_is_gone(worker_pid) and time.monotonic() < deadline:
            time.sleep(0.1)
        assert process_is_gone(worker_pid)
