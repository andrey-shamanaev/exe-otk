# -*- coding: utf-8 -*-
"""Загрузка и сохранение JSON с учётом сетевой папки (атомарная запись)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from typing import Any, Optional


def get_base_dir() -> str:
    """Папка с exe (при freeze) или папка скрипта. Не sys._MEIPASS."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    # main.py лежит в корне проекта
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def path(*parts: str) -> str:
    return os.path.join(get_base_dir(), *parts)


def _atomic_write(filepath: str, data: Any) -> None:
    """Запись через временный файл + replace (безопаснее на сетевых шарах)."""
    directory = os.path.dirname(filepath) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        # Несколько попыток replace (сетевые диски иногда блокируют)
        last_err: Optional[Exception] = None
        for _ in range(5):
            try:
                os.replace(tmp, filepath)
                return
            except OSError as e:
                last_err = e
                time.sleep(0.15)
        if last_err:
            raise last_err
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise


def load_json(name: str, default: Any) -> Any:
    filepath = path(name)
    if not os.path.isfile(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(name: str, data: Any) -> None:
    _atomic_write(path(name), data)


def load_questions() -> list:
    raw = load_json("questions.json", [])
    if not isinstance(raw, list):
        return []
    out = []
    for q in raw:
        out.append({
            "id": q.get("id"),
            "num": q.get("num"),
            "part": int(q.get("part") or 1),
            "topic": q.get("topic") or "",
            "question": q.get("question") or q.get("q") or "",
            "options": list(q.get("options") or q.get("opts") or []),
            "correct": q.get("correct"),
            "clause": q.get("clause") or "",
            "explain": q.get("explain") or "",
            "image": q.get("image") or None,
        })
    return out


def load_results() -> list:
    data = load_json("results.json", [])
    return data if isinstance(data, list) else []


def save_results(results: list) -> None:
    save_json("results.json", results)


def append_result(attempt: dict) -> None:
    results = load_results()
    results.append(attempt)
    save_results(results)


def load_lock() -> dict:
    data = load_json("lock.json", {"until": 0})
    if not isinstance(data, dict):
        return {"until": 0}
    return data


def save_lock(lock: dict) -> None:
    save_json("lock.json", lock)


def image_path(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    p = path(name)
    return p if os.path.isfile(p) else None
