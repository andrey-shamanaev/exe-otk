# -*- coding: utf-8 -*-
"""Главное окно приложения."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox, ttk

from app.config import APP_TITLE, LOCK_TIMEOUT_MS
from app.logic import build_attempt
from app import storage
from ui.start_frame import StartFrame
from ui.test_frame import TestFrame
from ui.result_frame import ResultFrame
from ui.admin_frame import AdminFrame, ask_admin_password


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("780x720")
        self.minsize(640, 520)

        self.questions = storage.load_questions()
        self.has_lock = False
        self.lock_timeout_ms = LOCK_TIMEOUT_MS

        style = ttk.Style(self)
        try:
            style.theme_use("vista" if sys.platform == "win32" else "clam")
        except Exception:
            pass

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.start_frame = StartFrame(self.container, self)
        self.test_frame = TestFrame(self.container, self)
        self.result_frame = ResultFrame(self.container, self)
        self.admin_frame = AdminFrame(self.container, self)

        for fr in (self.start_frame, self.test_frame, self.result_frame, self.admin_frame):
            fr.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.show_start()

        if not self.questions:
            messagebox.showwarning(
                "Вопросы",
                "Не найден questions.json рядом с программой.\n"
                f"Ожидаемый путь: {storage.path('questions.json')}",
            )

    def _show(self, frame):
        frame.lift()
        if hasattr(frame, "on_show"):
            frame.on_show()

    def show_start(self):
        self.start_frame.fio_entry.delete(0, "end")
        self._show(self.start_frame)

    def show_admin_login(self):
        if ask_admin_password(self):
            self._show(self.admin_frame)

    def start_test(self, fio: str, part: int, questions: list):
        self.test_frame.start(fio, part, questions)
        self._show(self.test_frame)

    def finish_test(self, state: dict):
        attempt = build_attempt(
            fio=state["fio"],
            part=state["part"],
            questions=state["questions"],
            answers=state["answers"],
            times=state["times"],
            started_at=state["startedAt"],
        )
        try:
            storage.append_result(attempt)
        except Exception as e:
            messagebox.showerror(
                "Сохранение",
                f"Не удалось сохранить результат в results.json.\n\n{e}",
            )
        self._release_lock()
        self.result_frame.show_result(attempt)
        self._show(self.result_frame)

    def _release_lock(self):
        if not self.has_lock:
            return
        try:
            storage.save_lock({"until": 0})
        except Exception:
            pass
        self.has_lock = False

    def _on_close(self):
        if self.test_frame.state and self.test_frame.state.get("active"):
            if not messagebox.askyesno(
                "Выход",
                "Тест ещё не завершён. Выйти и снять блокировку?",
            ):
                return
            self.test_frame.force_release()
        self._release_lock()
        self.destroy()


def run():
    app = App()
    app.mainloop()
