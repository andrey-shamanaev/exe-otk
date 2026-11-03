# -*- coding: utf-8 -*-
"""Экран результата для сотрудника."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.logic import format_duration


class ResultFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._build()

    def _build(self):
        self.lbl_score = ttk.Label(self, text="", font=("Segoe UI", 36, "bold"))
        self.lbl_score.pack(pady=(28, 8))

        self.lbl_summary = ttk.Label(self, text="", font=("Segoe UI", 11), wraplength=620)
        self.lbl_summary.pack(pady=(0, 12))

        ttk.Label(self, text="Разбор ошибок", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20)

        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True, padx=16, pady=8)

        self.canvas = tk.Canvas(wrap, highlightthickness=0)
        scroll = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        btn = ttk.Button(self, text="На главную", command=self._back)
        btn.pack(pady=16)

    def _on_mousewheel(self, event):
        if self.winfo_ismapped():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def show_result(self, attempt: dict):
        pct = attempt.get("percent") or 0
        if pct >= 80:
            color = "#16a34a"
        elif pct >= 60:
            color = "#d97706"
        else:
            color = "#dc2626"
        self.lbl_score.config(text=f"{pct}%", foreground=color)
        self.lbl_summary.config(
            text=(
                f"Верно {attempt.get('correct', 0)} из {attempt.get('total', 0)} · "
                f"неверно {attempt.get('wrong', 0)} · без ответа {attempt.get('empty', 0)} · "
                f"время {format_duration(attempt.get('durationMs'))}"
            )
        )

        for w in self.inner.winfo_children():
            w.destroy()

        mistakes = [
            (i + 1, it)
            for i, it in enumerate(attempt.get("items") or [])
            if not it.get("isCorrect")
        ]
        if not mistakes:
            ttk.Label(self.inner, text="Ошибок нет — отличный результат!", foreground="#16a34a").pack(
                anchor="w", padx=8, pady=8
            )
            return

        for num, it in mistakes:
            fr = ttk.LabelFrame(self.inner, text=f"Вопрос {num} · {it.get('topic') or ''}", padding=10)
            fr.pack(fill="x", padx=4, pady=6)
            ttk.Label(fr, text=it.get("question") or "", wraplength=580, font=("Segoe UI", 10)).pack(anchor="w")
            chosen = it.get("chosenText") if it.get("answered") else "— (без ответа)"
            ttk.Label(fr, text=f"Ваш ответ: {chosen}", foreground="#b91c1c").pack(anchor="w", pady=(6, 0))
            ttk.Label(fr, text=f"Правильно: {it.get('correctText') or '—'}", foreground="#15803d").pack(anchor="w")
            clause = it.get("clause") or ""
            if clause:
                ttk.Label(fr, text=clause, foreground="#64748b").pack(anchor="w", pady=(4, 0))
            explain = it.get("explain") or ""
            if explain:
                ttk.Label(fr, text=explain, wraplength=580, foreground="#475569").pack(anchor="w")

    def _back(self):
        self.app.show_start()
