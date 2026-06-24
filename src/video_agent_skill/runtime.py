from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class RuntimeContext:
    work_dir: Path
    keep_temp: bool = False

    def cleanup(self) -> None:
        if self.keep_temp:
            return
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)


def create_runtime_context(*, temp_dir: str = "", keep_temp: bool = False) -> RuntimeContext:
    base_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir())
    work_dir = base_dir / f"video-agent-{uuid4().hex}"
    work_dir.mkdir(parents=True, exist_ok=False)
    return RuntimeContext(work_dir=work_dir, keep_temp=keep_temp)
