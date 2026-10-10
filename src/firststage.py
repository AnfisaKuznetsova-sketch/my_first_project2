#!/usr/bin/env python3
"""Прототип эмулятора оболочки с виртуальной файловой системой.

Параметры командной строки:
    --vfs PATH      путь к ZIP-архиву с VFS
    --script PATH   путь к стартовому скрипту с командами
"""

import argparse
import os
import socket
import sys
import tkinter as tk
from tkinter import scrolledtext

from vfs import VirtualFS

running = True
vfs = VirtualFS()


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
    """Показывает содержимое каталога VFS."""
    path = args[0] if args else vfs.cwd
    target = vfs.absolute(path)

    if not vfs.is_dir(target):
        return f"Каталог не найден: {target}\n"

    files, dirs = vfs.list_dir(target)

    out = f"Содержимое {target}:\n"
    for d in dirs:
        out += f"  [dir]  {d}\n"
    for f in files:
        out += f"  [file] {f}\n"
    if not files and not dirs:
        out += "  (пусто)\n"
    return out


def cmd_cd(args):
    """Меняет текущий каталог VFS."""
    if not args:
        return f"Текущий каталог: {vfs.cwd}\n"

    if len(args) > 1:
        return (
            f"Ошибка: cd принимает один аргумент, "
            f"получено {len(args)}\n"
        )

    error = vfs.change_dir(args[0])
    if error:
        return error + "\n"
    return f"Текущий каталог: {vfs.cwd}\n"


def cmd_cat(args):
    """Показывает содержимое файла из VFS."""
    if not args:
        return "Ошибка: cat требует имя файла\n"
    if len(args) > 1:
        return (
            f"Ошибка: cat принимает один аргумент, "
            f"получено {len(args)}\n"
        )

    target = vfs.absolute(args[0])
    text, error = vfs.read_file(target)
    if error:
        return error + "\n"
    return text + "\n"


def cmd_pwd(args):
    """Показывает текущий каталог."""
    return vfs.cwd + "\n"


def cmd_vfs_init(args):
    """Заменяет текущую VFS на VFS из указанного ZIP-архива.

    Без аргументов возвращает VFS в пустое состояние
    (это и есть «VFS по умолчанию»).
    """
    global vfs

    if not args:
        vfs = VirtualFS()
        return "VFS сброшена в состояние по умолчанию.\n"

    if len(args) > 1:
        return (
            f"Ошибка: vfs-init принимает один аргумент, "
            f"получено {len(args)}\n"
        )

    new_vfs = VirtualFS()
    error = new_vfs.init_from_zip(args[0])
    if error:
        return error + "\n"

    vfs = new_vfs
    return f"VFS загружена из: {args[0]}\n"


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
        return cmd_cd(rest), False
    if cmd == "cat":
        return cmd_cat(rest), False
    if cmd == "pwd":
        return cmd_pwd(rest), False
    if cmd == "vfs-init":
        return cmd_vfs_init(rest), False
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
        help="путь к ZIP-архиву с VFS",
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
        if os.path.isfile(cli.vfs):
            print(f"[ok] VFS-архив существует: {cli.vfs}")
        else:
            print(f"[!] VFS-архив не найден: {cli.vfs}")

    if cli.script is not None:
        if os.path.isfile(cli.script):
            print(f"[ok] Стартовый скрипт существует: {cli.script}")
        else:
            print(f"[!] Стартовый скрипт не найден: {cli.script}")


def init_vfs_from_cli(cli):
    """Инициализирует VFS из ZIP-архива, если он задан."""
    if not cli.vfs:
        return
    error = vfs.init_from_zip(cli.vfs)
    if error:
        print(f"[!] {error}", file=sys.stderr)


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
    root.geometry("720x600")

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

    show("Эмулятор оболочки. Команды: ls, cd, cat, pwd, vfs-init, exit\n")
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
    init_vfs_from_cli(cli)

    root, show, entry = build_gui(cli)
    run_startup_script(cli, show, entry)

    root.mainloop()


if __name__ == "__main__":
    main()