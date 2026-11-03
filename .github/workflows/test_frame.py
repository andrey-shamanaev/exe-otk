# -*- coding: utf-8 -*-
"""Экран прохождения теста."""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox, ttk

from app.config import LIMITS_MS
from app.logic import format_clock
from app import storage

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class TestFrame(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.state = None
        self._photo = None
        self._timer_job = None
        self.answer_var = tk.IntVar(value=-1)
        self._build()

    def _build(self):
        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")

        left = ttk.Frame(top)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="Участник", foreground="#64748b", font=("Segoe UI", 9)).pack(anchor="w")
        self.lbl_fio = ttk.Label(left, text="", font=("Segoe UI", 12, "bold"))
        self.lbl_fio.pack(anchor="w")

        right = ttk.Frame(top)
        right.pack(side="right")
        self.lbl_part = ttk.Label(right, text="", foreground="#2563eb")
        self.lbl_part.pack(anchor="e")
        self.lbl_timer = ttk.Label(right, text="00:00", font=("Segoe UI", 16, "bold"))
        self.lbl_timer.pack(anchor="e")

        prog = ttk.Frame(self, padding=(12, 0))
        prog.pack(fill="x")
        self.progress = ttk.Progressbar(prog, mode="determinate", maximum=100)
        self.progress.pack(fill="x")
        self.lbl_counter = ttk.Label(prog, text="", foreground="#64748b")
        self.lbl_counter.pack(anchor="e")

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        self.lbl_topic = ttk.Label(body, text="", foreground="#0f766e", font=("Segoe UI", 10, "bold"))
        self.lbl_topic.pack(anchor="w", pady=(0, 6))

        self.lbl_question = ttk.Label(body, text="", wraplength=640, font=("Segoe UI", 12), justify="left")
        self.lbl_question.pack(anchor="w", pady=(0, 10))

        self.img_label = ttk.Label(body)
        self.img_label.pack(anchor="w", pady=(0, 10))

        self.opts_frame = ttk.Frame(body)
        self.opts_frame.pack(fill="x", anchor="w")

        nav = ttk.Frame(self, padding=12)
        nav.pack(fill="x", side="bottom")
        self.btn_prev = ttk.Button(nav, text="← Назад", command=self._prev)
        self.btn_prev.pack(side="left")
        self.btn_next = ttk.Button(nav, text="Далее →", command=self._next)
        self.btn_next.pack(side="right")

    def start(self, fio: str, part: int, questions: list):
        now = int(time.time() * 1000)
        self.state = {
            "fio": fio,
            "part": part,
            "questions": questions,
            "answers": [None] * len(questions),
            "times": [0] * len(questions),
            "current": 0,
            "startedAt": now,
            "questionEnteredAt": now,
            "active": True,
        }
        self.lbl_fio.config(text=fio)
        self.lbl_part.config(text=f"Часть {part}")
        self._render_question()
        self._schedule_timer()

    def _schedule_timer(self):
        self._cancel_timer()
        self._tick()
        self._timer_job = self.after(1000, self._schedule_timer)

    def _cancel_timer(self):
        if self._timer_job is not None:
            try:
                self.after_cancel(self._timer_job)
            except Exception:
                pass
            self._timer_job = None

    def _tick(self):
        st = self.state
        if not st or not st.get("active"):
            return
        elapsed = int(time.time() * 1000) - st["startedAt"]
        limit = LIMITS_MS.get(st["part"], 30 * 60 * 1000)
        self.lbl_timer.config(text=format_clock(elapsed))
        if elapsed > limit:
            self.lbl_timer.config(foreground="#dc2626")
        else:
            self.lbl_timer.config(foreground="#0f172a")

    def _leave_question(self):
        st = self.state
        if not st:
            return
        i = st["current"]
        st["times"][i] += int(time.time() * 1000) - st["questionEnteredAt"]

    def _render_question(self):
        st = self.state
        if not st:
            return
        qs = st["questions"]
        i = st["current"]
        total = len(qs)
        q = qs[i]

        answered = sum(1 for a in st["answers"] if a is not None)
        self.progress["value"] = (answered / total * 100) if total else 0
        self.lbl_counter.config(text=f"Вопрос {i + 1} из {total} · отвечено {answered}")

        self.lbl_topic.config(text=q.get("topic") or "")
        self.lbl_question.config(text=q.get("question") or "")

        # Image
        self.img_label.config(image="", text="")
        self._photo = None
        img_name = q.get("image")
        img_p = storage.image_path(img_name) if img_name else None
        if img_p and HAS_PIL:
            try:
                im = Image.open(img_p)
                im.thumbnail((620, 360), Image.Resampling.LANCZOS)
                self._photo = ImageTk.PhotoImage(im)
                self.img_label.config(image=self._photo)
            except Exception:
                pass
        elif img_p and not HAS_PIL:
            self.img_label.config(text=f"[картинка: {img_name}]")

        # Options
        for w in self.opts_frame.winfo_children():
            w.destroy()
        opts = q.get("options") or []
        cur = st["answers"][i]
        self.answer_var.set(cur if cur is not None else -1)
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for idx, text in enumerate(opts):
            letter = letters[idx] if idx < len(letters) else str(idx + 1)
            rb = ttk.Radiobutton(
                self.opts_frame,
                text=f"{letter}.  {text}",
                variable=self.answer_var,
                value=idx,
                command=lambda idx=idx: self._choose(idx),
            )
            rb.pack(anchor="w", pady=3)

        self.btn_prev.state(["!disabled"] if i > 0 else ["disabled"])
        is_last = i == total - 1
        self.btn_next.config(text="Завершить" if is_last else "Далее →")

    def _choose(self, idx: int):
        st = self.state
        if not st:
            return
        st["answers"][st["current"]] = idx
        answered = sum(1 for a in st["answers"] if a is not None)
        total = len(st["questions"])
        self.progress["value"] = (answered / total * 100) if total else 0
        self.lbl_counter.config(text=f"Вопрос {st['current'] + 1} из {total} · отвечено {answered}")

    def _prev(self):
        st = self.state
        if not st or st["current"] == 0:
            return
        self._leave_question()
        st["current"] -= 1
        st["questionEnteredAt"] = int(time.time() * 1000)
        self._render_question()

    def _next(self):
        st = self.state
        if not st:
            return
        total = len(st["questions"])
        is_last = st["current"] == total - 1
        if is_last:
            unanswered = sum(1 for a in st["answers"] if a is None)
            if unanswered > 0:
                if not messagebox.askyesno(
                    "Завершение",
                    f"Без ответа: {unanswered} из {total}. Завершить тест?",
                ):
                    return
            self._leave_question()
            self._finish()
            return
        self._leave_question()
        st["current"] += 1
        st["questionEnteredAt"] = int(time.time() * 1000)
        self._render_question()

    def _finish(self):
        st = self.state
        if not st:
            return
        st["active"] = False
        self._cancel_timer()
        self.app.finish_test(st)

    def force_release(self):
        """При закрытии окна во время теста."""
        self._cancel_timer()
        if self.state and self.state.get("active"):
            self.state["active"] = False
