# -*- coding: utf-8 -*-
"""Админ-панель: сводка, сотрудники, CSV, очистка."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from datetime import datetime

from app.config import ADMIN_PASSWORD, PART_LABELS
from app.logic import aggregate_admin, export_csv_text, format_duration, format_seconds, get_finished_at
from app import storage


class AdminFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._build()

    def _build(self):
        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")
        ttk.Label(top, text="Отчёт администратора", font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Button(top, text="← На главную", command=self.app.show_start).pack(side="right")

        # Summary cards
        self.sum_frame = ttk.Frame(self, padding=12)
        self.sum_frame.pack(fill="x")
        self.sum_labels = {}
        for key, title in (
            ("attempts", "Попыток"),
            ("employees", "Сотрудников"),
            ("avg_percent", "Средний %"),
            ("pass80", "≥ 80%"),
        ):
            fr = ttk.LabelFrame(self.sum_frame, text=title, padding=10)
            fr.pack(side="left", padx=6, expand=True, fill="x")
            lbl = ttk.Label(fr, text="0", font=("Segoe UI", 18, "bold"))
            lbl.pack()
            self.sum_labels[key] = lbl

        actions = ttk.Frame(self, padding=(12, 0))
        actions.pack(fill="x")
        ttk.Button(actions, text="Скачать результаты", command=self._export).pack(side="left", padx=4)
        ttk.Button(actions, text="Очистить всё", command=self._clear).pack(side="left", padx=4)
        ttk.Button(actions, text="Обновить", command=self.refresh).pack(side="left", padx=4)

        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=12, pady=8)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=1)

        ttk.Label(left, text="Сотрудники", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.emp_list = tk.Listbox(left, height=12, font=("Segoe UI", 10))
        self.emp_list.pack(fill="both", expand=True, pady=4)
        self.emp_list.bind("<<ListboxSelect>>", self._on_emp_select)

        self.emp_detail = ttk.Frame(left)
        self.emp_detail.pack(fill="x", pady=4)

        ttk.Label(right, text="Сложные вопросы (часто ошибаются)", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.hard_text = tk.Text(right, height=10, wrap="word", font=("Segoe UI", 9))
        self.hard_text.pack(fill="both", expand=True, pady=4)

        ttk.Label(self, text="Детализация попытки", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12)
        self.detail_text = tk.Text(self, height=12, wrap="word", font=("Consolas", 9))
        self.detail_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._by_fio = {}
        self._results = []

    def on_show(self):
        self.refresh()

    def refresh(self):
        results = storage.load_results()
        self._results = results
        agg = aggregate_admin(results)
        self._by_fio = agg["by_fio"]

        self.sum_labels["attempts"].config(text=str(agg["attempts"]))
        self.sum_labels["employees"].config(text=str(agg["employees"]))
        self.sum_labels["avg_percent"].config(text=f"{agg['avg_percent']}%")
        self.sum_labels["pass80"].config(text=str(agg["pass80"]))

        self.emp_list.delete(0, "end")
        for fio in sorted(self._by_fio.keys(), key=lambda s: s.lower()):
            attempts = self._by_fio[fio]
            percents = [a.get("percent") or 0 for a in attempts]
            avg = round(sum(percents) / len(percents)) if percents else 0
            best = max(percents) if percents else 0
            self.emp_list.insert("end", f"{fio}  ·  ср. {avg}%  ·  лучш. {best}%  ·  n={len(attempts)}")

        self.hard_text.delete("1.0", "end")
        if not agg["hard_questions"]:
            self.hard_text.insert("end", "Недостаточно данных.")
        else:
            for h in agg["hard_questions"]:
                self.hard_text.insert(
                    "end",
                    f"[{h['rate']}% ошибочных, {h['wrong']}/{h['total']}] {h['topic']}\n"
                    f"  {h['question'][:120]}\n\n",
                )

        self.detail_text.delete("1.0", "end")
        for w in self.emp_detail.winfo_children():
            w.destroy()

    def _on_emp_select(self, _event=None):
        sel = self.emp_list.curselection()
        if not sel:
            return
        line = self.emp_list.get(sel[0])
        fio = line.split("  ·  ")[0].strip()
        attempts = self._by_fio.get(fio) or []
        for w in self.emp_detail.winfo_children():
            w.destroy()

        ttk.Label(self.emp_detail, text=f"Попытки: {fio}", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        for a in sorted(attempts, key=lambda x: str(get_finished_at(x)), reverse=True):
            finished = get_finished_at(a)
            try:
                if isinstance(finished, (int, float)) and finished > 1e12:
                    ds = datetime.fromtimestamp(finished / 1000.0).strftime("%d.%m.%Y %H:%M")
                else:
                    ds = str(finished)[:19]
            except Exception:
                ds = str(finished)
            part = a.get("part")
            pl = PART_LABELS.get(int(part) if part is not None else 0, str(part))
            btn = ttk.Button(
                self.emp_detail,
                text=f"{ds} · ч.{part} · {a.get('percent')}% · {format_duration(a.get('durationMs'))}",
                command=lambda att=a: self._show_attempt(att),
            )
            btn.pack(fill="x", pady=2)

    def _show_attempt(self, attempt: dict):
        self.detail_text.delete("1.0", "end")
        lines = [
            f"ФИО: {attempt.get('fio')}",
            f"Часть: {attempt.get('part')} · {attempt.get('percent')}%",
            f"Верно/неверно/пусто: {attempt.get('correct')}/{attempt.get('wrong')}/{attempt.get('empty')}",
            f"Время: {format_duration(attempt.get('durationMs'))}",
            "",
        ]
        for i, it in enumerate(attempt.get("items") or []):
            if it.get("isCorrect"):
                st = "ВЕРНО"
            elif it.get("answered"):
                st = "НЕВЕРНО"
            else:
                st = "ПУСТО"
            lines.append(
                f"{i + 1}. [{st}] {format_seconds(it.get('timeMs'))} | {it.get('topic') or ''}"
            )
            lines.append(f"   Q: {(it.get('question') or '')[:100]}")
            if it.get("answered"):
                lines.append(f"   Ответ: {it.get('chosenText')}")
            if not it.get("isCorrect"):
                lines.append(f"   Правильно: {it.get('correctText')}")
                if it.get("clause"):
                    lines.append(f"   {it.get('clause')}")
            lines.append("")
        self.detail_text.insert("end", "\n".join(lines))

    def _export(self):
        results = storage.load_results()
        if not results:
            messagebox.showinfo("Экспорт", "Нет данных")
            return
        text = export_csv_text(results)
        path = filedialog.asksaveasfilename(
            title="Скачать результаты",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Все файлы", "*.*")],
            initialfile="results_sp53.csv",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                f.write(text)
            messagebox.showinfo("Экспорт", f"Сохранено:\n{path}")
        except Exception as e:
            messagebox.showerror("Экспорт", str(e))

    def _clear(self):
        if not messagebox.askyesno("Очистить", "Удалить все сохранённые результаты? Действие необратимо."):
            return
        try:
            storage.save_results([])
            self.refresh()
            messagebox.showinfo("Очистить", "Результаты очищены.")
        except Exception as e:
            messagebox.showerror("Очистить", str(e))


def ask_admin_password(parent) -> bool:
    pwd = simpledialog.askstring("Админ", "Пароль администратора:", show="*", parent=parent)
    if pwd is None:
        return False
    if pwd != ADMIN_PASSWORD:
        messagebox.showerror("Админ", "Неверный пароль", parent=parent)
        return False
    return True
