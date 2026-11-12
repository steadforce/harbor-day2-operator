"""Watch mode: run the synchronization repeatedly without a shell.

Until now the container was started as ``watch -n 60 /bin/ash <loader script>``: a shell script read the mounted secret files into
environment variables and started the operator once per cycle. This module does the same without a shell, so the image does not
need one:

* every cycle runs in a **fresh child process** with a freshly built environment. Several modules read their settings at import time,
  so only a new process picks up a refreshed secret; a failing or hanging cycle cannot damage the next one either;
* the secrets are read from the mounted files again in every cycle (the kubelet updates mounted secret volumes in place);
* a failed cycle is logged and the loop continues, like ``watch`` does. A cycle that runs longer than the timeout is terminated.
"""

from __future__ import annotations

import logging
import math
import os
import re
import signal
import subprocess
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

DEFAULT_INTERVAL = 60
DEFAULT_CYCLE_TIMEOUT = 900
DEFAULT_SECRETS_DIR = "/run/secrets"

# Layout of the mounted secrets (same as the loader script that this module replaces), below the secrets directory:
#   harbor-admin-credentials/harbor-admin-password-new  -> ADMIN_PASSWORD_NEW
#   harbor-admin-credentials/harbor-admin-password-old  -> ADMIN_PASSWORD_OLD
#   harbor-robot-tokens/<KEY>, oidc-static-client-token/<KEY> -> the environment variable <KEY> (like envFrom)
ADMIN_DIR = "harbor-admin-credentials"
ADMIN_FILES = {
    "harbor-admin-password-new": "ADMIN_PASSWORD_NEW",
    "harbor-admin-password-old": "ADMIN_PASSWORD_OLD",
}
ENV_FROM_DIRS = ("harbor-robot-tokens", "oidc-static-client-token")
# A file name becomes an environment variable only if it is a valid name; this skips the hidden entries of a Kubernetes secret volume.
VALID_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Time a child gets to exit after SIGTERM before it is killed
TERMINATE_GRACE_SECONDS = 10
POLL_SECONDS = 0.5

# Exit code reported for a cycle that was terminated because it ran too long
TIMEOUT_EXIT_CODE = -1


class StopLike:
    """The part of threading.Event that the loop needs (a test can replace it)."""

    def is_set(self) -> bool:  # pragma: no cover - interface only
        """Whether the loop should stop."""
        raise NotImplementedError

    def wait(
        self, timeout: float | None = None
    ) -> bool:  # pragma: no cover - interface only
        """Wait up to timeout seconds, return True when the loop should stop."""
        raise NotImplementedError


def _read_secret(path: Path) -> str:
    """Read a secret file like ``$(cat file)`` in a shell: trailing newlines are removed, everything else is kept.

    The bytes are decoded as they are; reading in text mode would turn a carriage return into a newline and change the secret.
    """
    return path.read_bytes().decode("utf-8").rstrip("\n")


def load_secret_env(secrets_dir: str | Path) -> dict[str, str]:
    """Build the environment variables that the mounted secrets provide.

    Missing directories and files are skipped: a variable that is not provided by a file keeps the value of the environment.

    Args:
        secrets_dir: Directory the secrets are mounted below

    Returns:
        dict[str, str]: Environment variables read from the files
    """
    base = Path(secrets_dir)
    env: dict[str, str] = {}

    for file_name, variable in ADMIN_FILES.items():
        path = base / ADMIN_DIR / file_name
        if path.is_file():
            env[variable] = _read_secret(path)

    for directory in ENV_FROM_DIRS:
        folder = base / directory
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file() and VALID_ENV_NAME.match(path.name):
                env[path.name] = _read_secret(path)

    return env


def parse_watch_args(argv: Sequence[str], environ: Mapping[str, str]) -> int | None:
    """Return the interval in seconds when ``--watch`` is given, otherwise None.

    ``--watch`` takes an optional number of seconds; without it the variable WATCH_INTERVAL or 60 is used.

    Args:
        argv: Command line arguments without the program name
        environ: Environment variables

    Returns:
        int | None: Interval in seconds, or None for a single run

    Raises:
        ValueError: If the interval is not a positive whole number
    """
    if "--watch" not in argv:
        return None
    index = list(argv).index("--watch")
    raw = (
        argv[index + 1]
        if index + 1 < len(argv) and not argv[index + 1].startswith("--")
        else None
    )
    value = (
        raw if raw is not None else environ.get("WATCH_INTERVAL", str(DEFAULT_INTERVAL))
    )
    try:
        interval = int(value)
    except ValueError:
        interval = 0
    if interval <= 0:
        raise ValueError(
            f"The watch interval must be a positive number of seconds, got '{value}'"
        )
    return interval


def parse_cycle_timeout(environ: Mapping[str, str]) -> float:
    """Return the maximum run time of one cycle in seconds (CYCLE_TIMEOUT, default 900).

    Args:
        environ: Environment variables

    Returns:
        float: Timeout in seconds

    Raises:
        ValueError: If CYCLE_TIMEOUT is not a positive, finite number
    """
    value = environ.get("CYCLE_TIMEOUT", str(DEFAULT_CYCLE_TIMEOUT))
    try:
        timeout = float(value)
    except ValueError:
        timeout = 0.0
    # nan and inf would never end a cycle, zero and negative numbers would end every cycle at once
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError(
            f"CYCLE_TIMEOUT must be a positive number of seconds, got '{value}'"
        )
    return timeout


def build_child_argv(
    frozen: bool, module_name: str | None, script_path: str, executable: str
) -> list[str]:
    """Return the command that runs a single synchronization.

    * A frozen executable (PyInstaller) starts itself.
    * Started as a module (``python -m src.harbor``) the child is started as the same module. Running the file instead would put
      its directory first on the module search path, and the ``from src...`` imports would fail.
    * Otherwise the file is run again (the module search path is inherited through PYTHONPATH).

    Args:
        frozen: Whether the program is a frozen executable
        module_name: Name of the running module (``__spec__.name``), None when run as a file
        script_path: Path of the running file
        executable: The Python interpreter or the frozen executable

    Returns:
        list[str]: Command of the child
    """
    if frozen:
        return [executable]
    if module_name:
        return [executable, "-m", module_name]
    return [executable, script_path]


def _signal_group(process: subprocess.Popen, signum: int) -> None:
    """Send a signal to the process group of the child; a group that is gone already is fine."""
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        pass


def run_child(
    argv: Sequence[str],
    env: Mapping[str, str],
    timeout: float,
    stop: StopLike,
) -> int:
    """Run one cycle in a child process and wait for it.

    The child is terminated (SIGTERM, then SIGKILL after a grace period) when it runs longer than the timeout or when the loop is
    asked to stop.

    Args:
        argv: Command of the child
        env: Environment of the child
        timeout: Maximum run time in seconds
        stop: Stop signal of the loop

    Returns:
        int: Exit code of the child, TIMEOUT_EXIT_CODE if it had to be terminated
    """
    # Own process group: a frozen onefile executable consists of a bootloader and the worker below it, and a SIGKILL of the bootloader
    # alone would leave the worker running into the next cycle. The signals go to the whole group.
    process = subprocess.Popen(list(argv), env=dict(env), start_new_session=True)
    waited = 0.0
    while True:
        try:
            return process.wait(timeout=POLL_SECONDS)
        except subprocess.TimeoutExpired:
            waited += POLL_SECONDS
            if waited >= timeout or stop.is_set():
                break
    _signal_group(process, signal.SIGTERM)
    try:
        process.wait(timeout=TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    # Also after a clean exit of the first process: kill whatever of the group is left
    _signal_group(process, signal.SIGKILL)
    process.wait()
    return TIMEOUT_EXIT_CODE


def watch_loop(
    run_cycle: Callable[[], int],
    interval: float,
    stop: StopLike,
    logger: logging.Logger,
) -> None:
    """Run cycles until stopped; a failing cycle is logged and the loop continues.

    Args:
        run_cycle: Runs one cycle and returns its exit code
        interval: Seconds to wait after a cycle
        stop: Stop signal
        logger: Logger for failed cycles
    """
    while not stop.is_set():
        try:
            exit_code = run_cycle()
            if exit_code != 0 and not stop.is_set():
                # The values are also in the message: the text log format ignores the extra fields
                logger.error(
                    "Synchronization cycle failed (exit code %s)",
                    exit_code,
                    extra={"exit_code": exit_code},
                )
        except Exception as e:  # noqa: BLE001 - a broken cycle must not end the loop
            logger.error(
                "Synchronization cycle could not run: %s", e, extra={"error": str(e)}
            )
        stop.wait(interval)


def run_watch(
    interval: int,
    child_argv: Sequence[str],
    logger: logging.Logger,
    environ: Mapping[str, str] | None = None,
) -> int:
    """Run the synchronization every ``interval`` seconds until SIGTERM or SIGINT.

    Args:
        interval: Seconds between cycles
        child_argv: Command that runs a single synchronization
        logger: Logger
        environ: Environment, defaults to os.environ

    Returns:
        int: Exit code of the program
    """
    environ = os.environ if environ is None else environ
    secrets_dir = environ.get("SECRETS_DIR", DEFAULT_SECRETS_DIR)
    timeout = parse_cycle_timeout(environ)

    stop = threading.Event()

    def request_stop(signum: int, _frame: object) -> None:
        logger.info("Stopping after signal %s", signum)
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    def run_cycle() -> int:
        child_env = {**environ, **load_secret_env(secrets_dir)}
        if getattr(sys, "frozen", False):
            # A onefile executable that starts itself would otherwise share the unpack directory of the parent
            child_env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        return run_child(child_argv, child_env, timeout, stop)

    logger.info("Watch mode: one synchronization every %s seconds", interval)
    watch_loop(run_cycle, interval, stop, logger)
    return 0
