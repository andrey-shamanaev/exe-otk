# -*- coding: utf-8 -*-
"""Бизнес-логика: завершение попытки, CSV, агрегаты админки."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Optional

from app.config import PART_LABELS


def format_clock(ms: float) -> str:
    total = max(0, int(ms // 1000))
    m, s = divmod(total, 60)
    return f"{m:02d}:{s:02d}"


def format_duration(ms: Optional[float]) -> str:
    if ms is None:
        return "—"
    total = int(round(ms / 1000))
    m, s = divmod(total, 60)
    if m > 0:
        return f"{m} мин {s:02d} с"
    return f"{s} с"


def format_seconds(ms: Optional[float]) -> str:
    if ms is None:
        return "—"
    try:
        s = float(ms) / 1000.0
    except (TypeError, ValueError):
        return "—"
    if s < 60:
        return f"{s:.1f} с"
    m = int(s // 60)
    return f"{m} мин {int(round(s % 60))} с"


def get_finished_at(attempt: dict) -> Any:
    return attempt.get("finishedAt") or attempt.get("finished_at") or attempt.get("startedAt") or 0


def build_attempt(
    fio: str,
    part: int,
    questions: list,
    answers: list,
    times: list,
    started_at: int,
) -> dict:
    finished_at = int(datetime.now().timestamp() * 1000)
    duration_ms = finished_at - started_at
    iso = datetime.fromtimestamp(finished_at / 1000.0).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    items = []
    for i, q in enumerate(questions):
        chosen = answers[i] if i < len(answers) else None
        opts = q.get("options") or []
        correct_idx = q.get("correct")
        answered = chosen is not None
        is_correct = answered and chosen == correct_idx
        items.append({
            "id": q.get("id"),
            "topic": q.get("topic") or "",
            "question": q.get("question") or "",
            "opts": opts,
            "correct": correct_idx,
            "clause": q.get("clause") or "",
            "explain": q.get("explain") or "",
            "answered": answered,
            "chosen": chosen,
            "chosenText": None if not answered else (opts[chosen] if 0 <= chosen < len(opts) else None),
            "correctText": opts[correct_idx] if isinstance(correct_idx, int) and 0 <= correct_idx < len(opts) else None,
            "isCorrect": is_correct,
            "timeMs": times[i] if i < len(times) else 0,
        })

    correct = sum(1 for it in items if it["isCorrect"])
    wrong = sum(1 for it in items if it["answered"] and not it["isCorrect"])
    empty = sum(1 for it in items if not it["answered"])
    total = len(items)
    percent = round(correct / total * 100) if total else 0

    return {
        "id": finished_at,
        "fio": fio,
        "part": part,
        "startedAt": started_at,
        "finishedAt": iso,
        "finished_at": iso,
        "durationMs": duration_ms,
        "correct": correct,
        "wrong": wrong,
        "empty": empty,
        "total": total,
        "percent": percent,
        "items": items,
    }


def export_csv_text(results: list) -> str:
    """Подробный CSV: строка на каждый ответ. Разделитель ';', UTF-8 BOM."""
    if not results:
        return ""

    by_fio: dict = {}
    for a in results:
        key = a.get("fio") or ""
        by_fio.setdefault(key, []).append(a)
    for lst in by_fio.values():
        lst.sort(key=lambda x: str(get_finished_at(x)))
        for i, a in enumerate(lst):
            a["_exportNum"] = i + 1

    headers = [
        "ФИО",
        "Дата завершения",
        "Часть теста",
        "№ попытки",
        "Результат %",
        "Верно",
        "Неверно",
        "Без ответа",
        "Всего вопросов",
        "Время попытки (сек)",
        "Время попытки",
        "№ вопроса",
        "Тема",
        "Вопрос",
        "Ответ сотрудника",
        "Правильный ответ",
        "Статус ответа",
        "Время на вопрос (сек)",
        "Пункт СП",
        "Пояснение",
    ]

    sorted_results = sorted(
        results,
        key=lambda a: ((a.get("fio") or ""), str(get_finished_at(a))),
    )

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow(headers)

    for a in sorted_results:
        finished = get_finished_at(a)
        date_str = ""
        try:
            if isinstance(finished, (int, float)) and finished > 1e12:
                date_str = datetime.fromtimestamp(finished / 1000.0).strftime("%d.%m.%Y %H:%M:%S")
            elif isinstance(finished, (int, float)) and finished > 1e9:
                date_str = datetime.fromtimestamp(finished).strftime("%d.%m.%Y %H:%M:%S")
            elif finished:
                date_str = datetime.fromisoformat(str(finished).replace("Z", "+00:00")).astimezone().strftime("%d.%m.%Y %H:%M:%S")
        except Exception:
            date_str = str(finished or "")

        part = a.get("part")
        part_label = PART_LABELS.get(int(part) if part is not None else 0, str(part or ""))

        duration_ms = a.get("durationMs")
        duration_sec = int(round(duration_ms / 1000)) if duration_ms is not None else ""
        duration_human = format_duration(duration_ms) if duration_ms is not None else ""
        attempt_num = a.get("_exportNum", "")

        items = a.get("items") or [None]
        for i, it in enumerate(items):
            if not it:
                writer.writerow([
                    a.get("fio") or "",
                    date_str,
                    part_label,
                    attempt_num,
                    a.get("percent", ""),
                    a.get("correct", ""),
                    a.get("wrong", ""),
                    a.get("empty", ""),
                    a.get("total", ""),
                    duration_sec,
                    duration_human,
                    "", "", "", "", "", "", "", "", "",
                ])
                continue

            if it.get("isCorrect"):
                status = "Верно"
            elif it.get("answered"):
                status = "Неверно"
            else:
                status = "Без ответа"

            time_ms = it.get("timeMs")
            time_sec = ""
            if time_ms is not None:
                try:
                    time_sec = f"{float(time_ms) / 1000.0:.1f}"
                except (TypeError, ValueError):
                    time_sec = ""

            writer.writerow([
                a.get("fio") or "",
                date_str,
                part_label,
                attempt_num,
                a.get("percent", ""),
                a.get("correct", ""),
                a.get("wrong", ""),
                a.get("empty", ""),
                a.get("total", ""),
                duration_sec,
                duration_human,
                i + 1,
                it.get("topic") or "",
                it.get("question") or "",
                it.get("chosenText") if it.get("answered") else "",
                it.get("correctText") or "",
                status,
                time_sec,
                it.get("clause") or "",
                it.get("explain") or "",
            ])

    # UTF-8 BOM
    return "\ufeff" + buf.getvalue()


def aggregate_admin(results: list) -> dict:
    """Сводка для админки."""
    if not results:
        return {
            "attempts": 0,
            "employees": 0,
            "avg_percent": 0,
            "pass80": 0,
            "hard_questions": [],
            "by_fio": {},
        }

    by_fio: dict = {}
    for a in results:
        fio = a.get("fio") or "—"
        by_fio.setdefault(fio, []).append(a)

    percents = [a.get("percent") or 0 for a in results]
    avg = round(sum(percents) / len(percents)) if percents else 0
    pass80 = sum(1 for p in percents if p >= 80)

    # Сложные вопросы: чаще всего отвечали неверно
    q_stats: dict = {}
    for a in results:
        for it in a.get("items") or []:
            key = (it.get("id") or it.get("question") or "")[:80]
            if not key:
                continue
            st = q_stats.setdefault(key, {
                "topic": it.get("topic") or "",
                "question": it.get("question") or "",
                "wrong": 0,
                "total": 0,
            })
            st["total"] += 1
            if it.get("answered") and not it.get("isCorrect"):
                st["wrong"] += 1

    hard = sorted(
        (
            {**v, "rate": round(v["wrong"] / v["total"] * 100) if v["total"] else 0}
            for v in q_stats.values()
            if v["total"] >= 2
        ),
        key=lambda x: (-x["rate"], -x["wrong"]),
    )[:15]

    return {
        "attempts": len(results),
        "employees": len(by_fio),
        "avg_percent": avg,
        "pass80": pass80,
        "hard_questions": hard,
        "by_fio": by_fio,
    }
