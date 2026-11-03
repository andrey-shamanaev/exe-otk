# -*- coding: utf-8 -*-
"""Экран старта: ФИО, выбор части, блокировка."""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox, ttk

from app.config import PART_DESCRIPTIONS, PART_LABELS
from app import storage


class StartFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.part_var = tk.IntVar(value=1)
        self._build()

    def _build(self):
        pad = {"padx": 20, "pady": 8}

        title = ttk.Label(self, text="Тестирование по СП 53-101-98", font=("Segoe UI", 18, "bold"))
        title.pack(pady=(24, 4))
        sub = ttk.Label(
            self,
            text="Изготовление и контроль качества стальных строительных конструкций",
            font=("Segoe UI", 10),
            foreground="#64748b",
        )
        sub.pack(pady=(0, 16))

        card = ttk.LabelFrame(self, text="Участник", padding=16)
        card.pack(fill="x", **pad)

        ttk.Label(card, text="ФИО", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.fio_entry = ttk.Entry(card, font=("Segoe UI", 12))
        self.fio_entry.pack(fill="x", pady=(4, 12))
        self.fio_entry.focus_set()

        ttk.Label(card, text="Часть теста", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.part_frames = []
        for part in (1, 2):
            fr = ttk.Frame(card, relief="groove", borderwidth=1, padding=10)
            fr.pack(fill="x", pady=4)
            rb = ttk.Radiobutton(
                fr,
                text=PART_LABELS.get(part, f"Часть {part}"),
                variable=self.part_var,
                value=part,
            )
            rb.pack(anchor="w")
            desc = PART_DESCRIPTIONS.get(part, "")
            ttk.Label(fr, text=desc, wraplength=560, foreground="#64748b").pack(anchor="w", padx=(22, 0))
            count_lbl = ttk.Label(fr, text="", foreground="#2563eb")
            count_lbl.pack(anchor="w", padx=(22, 0), pady=(2, 0))
            self.part_frames.append((part, count_lbl))

        self.lock_frame = ttk.Frame(self, padding=10)
        self.lock_label = ttk.Label(
            self.lock_frame,
            text="",
            foreground="#b91c1c",
            font=("Segoe UI", 10, "bold"),
            wraplength=600,
        )
        self.lock_label.pack()
        self.lock_frame.pack(fill="x", **pad)
        self.lock_frame.pack_forget()

        self.btn_start = ttk.Button(self, text="Начать тестирование", command=self._on_start)
        self.btn_start.pack(pady=12, ipadx=20, ipady=6)

        foot = ttk.Frame(self)
        foot.pack(side="bottom", fill="x", pady=16, padx=20)
        ttk.Label(foot, text="СП 53-101-98", foreground="#94a3b8").pack(side="left")
        ttk.Button(foot, text="Отчёт для администратора", command=self.app.show_admin_login).pack(side="right")

    def on_show(self):
        self.refresh_counts()
        self.refresh_lock()
        self.fio_entry.focus_set()

    def refresh_counts(self):
        qs = self.app.questions
        for part, lbl in self.part_frames:
            n = sum(1 for q in qs if q.get("part") == part)
            lbl.config(text=f"Вопросов: {n}")

    def refresh_lock(self):
        lock = storage.load_lock()
        until = lock.get("until") or 0
        now = int(time.time() * 1000)
        if until > now:
            left = max(1, int((until - now) / 60000))
            fio = lock.get("fio") or "другой пользователь"
            self.lock_label.config(
                text=f"Сайт занят. Сейчас тестирование проходит: {fio} (ещё ~{left} мин). Новый тест начать нельзя."
            )
            self.lock_frame.pack(fill="x", padx=20, pady=8)
            self.btn_start.state(["disabled"])
            return False
        self.lock_frame.pack_forget()
        self.btn_start.state(["!disabled"])
        return True

    def _on_start(self):
        fio = self.fio_entry.get().strip()
        if not fio:
            messagebox.showwarning("ФИО", "Укажите ФИО")
            return
        if not self.refresh_lock():
            return
        part = self.part_var.get()
        list_q = [q for q in self.app.questions if q.get("part") == part]
        if not list_q:
            messagebox.showwarning("Часть", "В выбранной части нет вопросов.")
            return
        try:
            storage.save_lock({
                "fio": fio,
                "since": int(time.time() * 1000),
                "until": int(time.time() * 1000) + self.app.lock_timeout_ms,
            })
            self.app.has_lock = True
        except Exception as e:
            messagebox.showerror(
                "Блокировка",
                f"Не удалось занять сайт (запись lock.json).\n\n{e}",
            )
            return
        self.app.start_test(fio, part, list_q)
