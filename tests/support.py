"""Fail closed on network, child processes, or any access to the operator's state."""
import importlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def safety():
    forbidden = (Path.home() / ".signal").resolve()

    def audit(event, args):
        # Linux 의 ctypes.util.find_library(텔레그램 라이브러리 import 시)는 읽기 전용 `ldconfig -p` 만 실행한다 — 이것 하나만 허용
        if event == "subprocess.Popen" and list(args[1] or []) in (["/sbin/ldconfig", "-p"], ["ldconfig", "-p"]):
            return
        if event in ("socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"):
            raise RuntimeError("TEST SAFETY: real network/process blocked: " + event)
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).resolve()
            if path == forbidden or forbidden in path.parents:
                raise PermissionError("TEST SAFETY: operator state access blocked")

    sys.addaudithook(audit)


def repository_modules():
    if not (ROOT / "tools").is_dir():   # 공개 저장소: Mac 작업 코드가 없다(그 검사도 없다)
        return
    sys.path.insert(0, str(ROOT / "tools"))
    for name in ("ds_client", "tg_publish", "daily_brief", "econ_brief", "theme_brief", "story_threads", "release_watch"):
        sys.path[:] = [p for p in sys.path if Path(p).resolve() != Path.home() / ".signal"]
        module = importlib.import_module(name)
        assert Path(module.__file__).resolve().parent == ROOT / "tools", name
    # story_threads prepends its installation directory even at import time.
    sys.path[:] = [p for p in sys.path if Path(p).resolve() != Path.home() / ".signal"]
