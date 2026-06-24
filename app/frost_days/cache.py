from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from frost_days.config import CACHE_DIR


class LocalCache:
    def __init__(self, root: Path = CACHE_DIR) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, namespace: str, key: str, suffix: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        folder = self.root / namespace
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{digest}.{suffix}"

    def get_json(self, namespace: str, key: str) -> Any | None:
        path = self._path(namespace, key, "json")
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def set_json(self, namespace: str, key: str, value: Any) -> None:
        path = self._path(namespace, key, "json")
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_dataframe(self, namespace: str, key: str) -> pd.DataFrame | None:
        path = self._path(namespace, key, "csv.gz")
        if not path.exists():
            return None
        return pd.read_csv(path, compression="gzip", low_memory=False)

    def set_dataframe(self, namespace: str, key: str, frame: pd.DataFrame) -> None:
        path = self._path(namespace, key, "csv.gz")
        frame.to_csv(path, index=False, compression="gzip")

    def get_pickle_dataframe(self, namespace: str, key: str) -> pd.DataFrame | None:
        path = self._path(namespace, key, "pkl")
        if not path.exists():
            return None
        return pd.read_pickle(path)

    def set_pickle_dataframe(self, namespace: str, key: str, frame: pd.DataFrame) -> None:
        path = self._path(namespace, key, "pkl")
        frame.to_pickle(path)
