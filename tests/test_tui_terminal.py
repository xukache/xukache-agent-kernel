from __future__ import annotations

import os
import pty
import select
import signal
import struct
import subprocess
import termios
import time
import fcntl
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _base_env(runtime_dir: Path, *, term: str = "xterm-256color") -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "ANANHU_RUNTIME_DIR": str(runtime_dir),
        "TERM": term,
    })
    for name in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        env.pop(name, None)
    return env


def _read_pty(
    pid: int, master_fd: int, timeout: float = 10.0
) -> tuple[str, int | None]:
    chunks: list[bytes] = []
    status: int | None = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        readable, _, _ = select.select([master_fd], [], [], 0.1)
        if readable:
            try:
                chunks.append(os.read(master_fd, 4096))
            except OSError:
                break
        waited_pid, status = os.waitpid(pid, os.WNOHANG)
        if waited_pid == pid:
            break
    return b"".join(chunks).decode("utf-8", errors="replace"), status


def _start_chat_pty(runtime_dir: Path):
    master_fd, slave_fd = pty.openpty()
    pid = os.fork()
    if pid == 0:
        os.setsid()
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        os.close(master_fd)
        os.close(slave_fd)
        os.chdir(PROJECT_ROOT)
        os.execvpe(
            "uv",
            ["uv", "run", "ananhu-agent", "chat"],
            _base_env(runtime_dir),
        )
    os.close(slave_fd)
    return pid, master_fd


def _finish_pty(
    pid: int, master_fd: int, *, send_resize: bool = False
) -> tuple[int, str]:
    try:
        if send_resize:
            fcntl_winsize = struct.pack("HHHH", 30, 100, 0, 0)
            fcntl.ioctl(master_fd, termios.TIOCSWINSZ, fcntl_winsize)
            os.kill(pid, signal.SIGWINCH)
            time.sleep(0.2)
        os.write(master_fd, b"\x03")
        output, status = _read_pty(pid, master_fd)
        if status is None:
            _, status = os.waitpid(pid, 0)
        return os.waitstatus_to_exitcode(status), output
    finally:
        try:
            waited_pid, _ = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            waited_pid = pid
        if waited_pid == 0:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        os.close(master_fd)


def test_chat_starts_and_ctrl_c_exits_in_real_pty(tmp_path: Path) -> None:
    pid, master_fd = _start_chat_pty(tmp_path)
    returncode, output = _finish_pty(pid, master_fd)

    assert returncode == 0
    assert "Traceback" not in output


def test_sigwinch_resize_keeps_chat_alive(tmp_path: Path) -> None:
    pid, master_fd = _start_chat_pty(tmp_path)
    returncode, output = _finish_pty(pid, master_fd, send_resize=True)

    assert returncode == 0
    assert "Traceback" not in output


def test_term_dumb_exits_two_with_clear_message(tmp_path: Path) -> None:
    result = subprocess.run(
        ["uv", "run", "ananhu-agent", "chat"],
        cwd=PROJECT_ROOT,
        env=_base_env(tmp_path, term="dumb"),
        input="",
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 2
    assert "ananhu-agent chat requires an interactive ANSI terminal" in result.stderr


def test_non_tty_exits_two_and_reaps_process(tmp_path: Path) -> None:
    process = subprocess.Popen(
        ["uv", "run", "ananhu-agent", "chat"],
        cwd=PROJECT_ROOT,
        env=_base_env(tmp_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate(input="", timeout=10)

    assert process.poll() is not None
    assert process.returncode == 2
    assert "ananhu-agent chat requires an interactive ANSI terminal" in stderr
    assert "Traceback" not in stdout + stderr
