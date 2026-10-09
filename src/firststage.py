import argparse
import os
import socket
import sys
import tkinter as tk
from tkinter import scrolledtext

running = True


def split_args(line):
    parts = []
    word = ""
    quote = ""
    for ch in line:
        if quote:
            if ch == quote:
                quote = ""
            else:
                word += ch
        elif ch == "'" or ch == '"':
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


def execute(line):
    global running
    args, bad = split_args(line)

    if bad:
        return "Ошибка: незакрытая кавычка\n", True
    if not args:
        return "", False

    cmd = args[0]
    rest = args[1:]

    if cmd == "ls":
        out = "ls\n"
        if not rest:
            out += "Аргументов нет\n"
        else:
            out += "Аргументы:\n"
            for i, a in enumerate(rest, 1):
                out += f"  [{i}] '{a}'\n"
        return out, False

    if cmd == "cd":
        out = "cd\n"
        if not rest:
            out += "Аргументов нет\n"
        elif len(rest) > 1:
            out += (
                f"Ошибка: cd принимает один аргумент, "
                f"получено {len(rest)}\n"
            )
            return out, True
        else:
            out += f"Аргументы:\n  [1] '{rest[0]}'\n"
        return out, False

    if cmd == "exit":
        running = False
        return "Завершение работы...\n", False

    return f"Команда не найдена: {cmd}\n", True


def parse_cli(argv):
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


def run_script(path, out_callback):
    """Прогоняет стартовый скрипт. Останавливается при первой ошибке."""
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


def main():
    """Точка входа: разбирает CLI, создаёт окно, при необходимости
    выполняет стартовый скрипт."""

    cli = parse_cli(sys.argv[1:])

    # ---------- Отладочный вывод всех параметров ----------
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

    root = tk.Tk()

    user = (
        os.environ.get("USER")
        or os.environ.get("USERNAME")
        or "user"
    )
    host = socket.gethostname()
    root.title(f"Эмулятор - [{user}@{host}]")
    root.geometry("700x600")

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

    def show(text):
        box.config(state="normal")
        box.insert(tk.END, text)
        box.see(tk.END)
        box.config(state="disabled")

    def on_enter(event):
        line = entry.get()
        entry.delete(0, tk.END)
        show("> " + line + "\n")
        answer, _ = execute(line)
        if answer:
            show(answer)
        show("\n")
        if not running:
            entry.config(state="disabled")

    entry.bind("<Return>", on_enter)

    show("Команды: ls, cd, exit\n")
    show(f"VFS:    {cli.vfs or '(не задан)'}\n")
    show(f"Script: {cli.script or '(не задан)'}\n\n")

    # ---------- Автовыполнение стартового скрипта ----------
    if cli.script:
        show(f"--- Запуск скрипта: {cli.script} ---\n")
        error = run_script(cli.script, show)

        if error:
            show(f"\n!!! {error}\n")
            print(f"ОШИБКА: {error}", file=sys.stderr)
        else:
            show("\n--- Скрипт завершён ---\n")

        if not running:
            entry.config(state="disabled")

    root.mainloop()


if __name__ == "__main__":
    main()