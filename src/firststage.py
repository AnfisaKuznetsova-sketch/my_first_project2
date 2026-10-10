#!/usr/bin/env python3
"""Прототип эмулятора оболочки.

Параметры командной строки:
    --vfs PATH      путь к физическому расположению VFS
    --script PATH   путь к стартовому скрипту с командами
"""

import argparse
import os
import socket
import sys
import tkinter as tk
from tkinter import scrolledtext

running = True


def split_args(line):
    """Разбивает строку на слова с учётом одинарных и двойных кавычек.

    Возвращает кортеж (список_слов, незакрытая_кавычка).
    """
    parts = []
    word = ""
    quote = ""
    for ch in line:
        if quote:
            if ch == quote:
                quote = ""
            else:
                word += ch
        elif ch in ("'", '"'):
            quote = ch
        elif ch == " ":
            if word:
                parts.append(word)
                word = ""
        else:
            word += ch
    if word:
        parts.append(word)
    return parts, quote


def cmd_ls(args):
    """Заглушка команды ls: печатает имя и аргументы."""
    out = "ls\n"
    if not args:
        out += "Аргументов нет\n"
    else:
        out += "Аргументы:\n"
        for i, a in enumerate(args, 1):
            out += f"  [{i}] '{a}'\n"
    return out


def cmd_cd(args):
    """Заглушка команды cd: печатает имя и аргументы.

    Возвращает кортеж (текст, была_ли_ошибка).
    """
    out = "cd\n"
    if not args:
        out += "Аргументов нет\n"
        return out, False
    if len(args) > 1:
        out += (
            f"Ошибка: cd принимает один аргумент, "
            f"получено {len(args)}\n"
        )
        return out, True
    out += f"Аргументы:\n  [1] '{args[0]}'\n"
    return out, False


def cmd_exit(args):
    """Завершает работу эмулятора."""
    global running
    running = False
    return "Завершение работы...\n"


def execute(line):
    """Выполняет одну строку.

    Возвращает кортеж (текст_ответа, была_ли_ошибка).
    """
    args, bad = split_args(line)

    if bad:
        return "Ошибка: незакрытая кавычка\n", True
    if not args:
        return "", False

    cmd = args[0]
    rest = args[1:]

    if cmd == "ls":
        return cmd_ls(rest), False
    if cmd == "cd":
        return cmd_cd(rest)
    if cmd == "exit":
        return cmd_exit(rest), False

    return f"Команда не найдена: {cmd}\n", True


def parse_cli(argv):
    """Разбирает параметры командной строки."""
    parser = argparse.ArgumentParser(
        prog="firststage",
        description="Эмулятор оболочки: GUI + параметры командной строки",
    )
    parser.add_argument(
        "--vfs",
        metavar="PATH",
        default=None,
        help="путь к физическому расположению VFS",
    )
    parser.add_argument(
        "--script",
        metavar="PATH",
        default=None,
        help="путь к стартовому скрипту с командами",
    )
    return parser.parse_args(argv)


def print_debug_info(cli):
    """Печатает отладочную информацию о параметрах запуска."""
    print("=== Параметры запуска эмулятора ===")
    print(f"  vfs    = {cli.vfs!r}")
    print(f"  script = {cli.script!r}")
    print("===================================")

    if cli.vfs is not None:
        if os.path.isdir(cli.vfs):
            print(f"[ok] VFS существует: {cli.vfs}")
        else:
            print(f"[!] VFS не найден: {cli.vfs}")

    if cli.script is not None:
        if os.path.isfile(cli.script):
            print(f"[ok] Стартовый скрипт существует: {cli.script}")
        else:
            print(f"[!] Стартовый скрипт не найден: {cli.script}")


def run_script(path, out_callback):
    """Прогоняет стартовый скрипт, останавливается при первой ошибке.

    Возвращает None при успехе или текст ошибки.
    """
    if not os.path.isfile(path):
        return f"Стартовый скрипт не найден: {path}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        return f"Ошибка чтения скрипта: {e}"

    for i, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        out_callback(f"> {line}\n")
        answer, was_error = execute(line)
        if answer:
            out_callback(answer)
        out_callback("\n")

        if was_error:
            return (
                f"Ошибка в стартовом скрипте "
                f"(строка {i}): {line}"
            )
    return None

def make_show(box):
    """Создаёт функцию show для вывода текста в область вывода."""
    def show(text):
        """Добавляет текст в область вывода."""
        box.config(state="normal")
        box.insert(tk.END, text)
        box.see(tk.END)
        box.config(state="disabled")
    return show


def make_on_enter(entry, show):
    """Создаёт обработчик Enter для строки ввода."""
    def on_enter(event):
        """Обрабатывает нажатие Enter в строке ввода."""
        line = entry.get()
        entry.delete(0, tk.END)
        show("> " + line + "\n")
        answer, _ = execute(line)
        if answer:
            show(answer)
        show("\n")
        if not running:
            entry.config(state="disabled")
    return on_enter


def build_gui(cli):
    """Создаёт окно и возвращает (root, show, entry)."""
    root = tk.Tk()
    user = (
        os.environ.get("USER")
        or os.environ.get("USERNAME")
        or "user"
    )
    host = socket.gethostname()
    root.title(f"Эмулятор - [{user}@{host}]")
    root.geometry("720x460")

    box = scrolledtext.ScrolledText(
        root,
        state="disabled",
        bg="black",
        fg="white",
        font=("Consolas", 11),
    )
    box.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 0))

    entry = tk.Entry(root, font=("Consolas", 12))
    entry.pack(fill=tk.X, padx=6, pady=6)
    entry.focus_set()

    show = make_show(box)
    entry.bind("<Return>", make_on_enter(entry, show))

    show("Эмулятор оболочки. Команды: ls, cd, exit\n")
    show(f"VFS:    {cli.vfs or '(не задан)'}\n")
    show(f"Script: {cli.script or '(не задан)'}\n\n")

    return root, show, entry


def run_startup_script(cli, show, entry):
    """Запускает стартовый скрипт, если он задан."""
    if not cli.script:
        return

    show(f"--- Запуск скрипта: {cli.script} ---\n")
    error = run_script(cli.script, show)

    if error:
        show(f"\n!!! {error}\n")
        print(f"ОШИБКА: {error}", file=sys.stderr)
    else:
        show("\n--- Скрипт завершён ---\n")

    if not running:
        entry.config(state="disabled")

def main():
    """Точка входа: разбор аргументов, создание GUI, запуск скрипта."""
    cli = parse_cli(sys.argv[1:])
    print_debug_info(cli)

    root, show, entry = build_gui(cli)
    run_startup_script(cli, show, entry)

    root.mainloop()

if __name__ == "__main__":
    main()