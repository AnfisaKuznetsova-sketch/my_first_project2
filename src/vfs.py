"""Виртуальная файловая система на базе ZIP-архива.

Архив читается в память и НЕ распаковывается на диск.
Все операции производятся над содержимым ZIP-архива.
"""

import io
import posixpath
import zipfile


class VirtualFS:
    """Виртуальная файловая система внутри ZIP-архива.

    Хранит карту файлов (путь -> bytes) и список папок.
    Все пути нормализуются к виду '/a/b/c'.
    """

    def __init__(self):
        """Создаёт пустую VFS без источника."""
        self.files = {}          # {путь: bytes}
        self.dirs = {"/"}        # множество папок, всегда есть корень
        self.cwd = "/"           # текущий каталог
        self.source = None       # путь к ZIP-архиву-источнику

    # ---------- Инициализация из ZIP ----------

    def init_from_zip(self, zip_path):
        """Загружает VFS из ZIP-архива. Читает в память, не распаковывает.

        Возвращает None при успехе или строку с текстом ошибки.
        """
        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                self._load_from_archive(archive)
        except FileNotFoundError:
            return f"ZIP-архив не найден: {zip_path}"
        except zipfile.BadZipFile:
            return f"Не удалось открыть ZIP-архив: {zip_path}"
        except OSError as e:
            return f"Ошибка чтения ZIP-архива: {e}"

        self.source = zip_path
        self.cwd = "/"
        return None

    def _load_from_archive(self, archive):
        """Заполняет карту файлов и папок из открытого ZIP-архива."""
        self.files = {}
        self.dirs = {"/"}

        for info in archive.infolist():
            if info.is_dir():
                self._add_dir(info.filename)
            else:
                self._add_file(archive, info)

    def _add_dir(self, name):
        """Добавляет папку и все её родительские папки."""
        path = "/" + name.strip("/")
        while path and path != "/":
            self.dirs.add(path)
            path = posixpath.dirname(path)

    def _add_file(self, archive, info):
        """Добавляет файл: путь, родительские папки, содержимое."""
        self._add_dir(info.filename)
        path = "/" + info.filename.strip("/")
        with archive.open(info) as f:
            self.files[path] = f.read()

    # ---------- Запросы ----------

    def exists(self, path):
        """Проверяет, что путь есть в VFS (файл или папка)."""
        return path in self.files or path in self.dirs

    def is_dir(self, path):
        """Проверяет, что путь — это папка."""
        return path in self.dirs

    def is_file(self, path):
        """Проверяет, что путь — это файл."""
        return path in self.files

    def list_dir(self, path):
        """Возвращает содержимое папки: два списка (файлы, папки).

        Если путь не папка — возвращает (None, None).
        """
        if not self.is_dir(path):
            return None, None

        prefix = path.rstrip("/") + "/"
        files = []
        dirs = []

        for f in self.files:
            if f.startswith(prefix):
                tail = f[len(prefix):]
                if "/" not in tail:
                    files.append(tail)

        for d in self.dirs:
            if d == path or d == "/":
                continue
            if d in self.files:        # это файл, не папка
                continue
            if d.startswith(prefix):
                tail = d[len(prefix):]
                if "/" not in tail and tail:
                    dirs.append(tail)

        return sorted(files), sorted(dirs)

    def read_file(self, path):
        """Читает файл из VFS. Возвращает (текст, ошибка).

        Текст декодируется как UTF-8 (с заменой некорректных байт).
        """
        if not self.is_file(path):
            return None, f"Файл не найден: {path}"
        data = self.files[path]
        return data.decode("utf-8", errors="replace"), None

    # ---------- Работа с путями ----------

    @staticmethod
    def normalize(path):
        """Приводит путь к каноническому виду '/a/b/c'."""
        if not path:
            return "/"
        if not path.startswith("/"):
            path = "/" + path
        path = posixpath.normpath(path)
        if not path.startswith("/"):
            path = "/" + path
        return path

    def absolute(self, path):
        """Возвращает абсолютный путь относительно текущего каталога."""
        if path.startswith("/"):
            return self.normalize(path)
        return self.normalize(posixpath.join(self.cwd, path))

    def change_dir(self, path):
        """Меняет текущий каталог. Возвращает None или текст ошибки."""
        target = self.absolute(path)
        if not self.is_dir(target):
            return f"Каталог не найден: {target}"
        self.cwd = target
        return None

    # ---------- Изменение VFS (только в памяти) ----------

    def create_file(self, path):
        """Создаёт пустой файл в VFS. Возвращает None или ошибку.

        Если файл уже существует — ничего не делает.
        Родительская папка должна существовать.
        """
        target = self.absolute(path)
        parent = posixpath.dirname(target)

        if not self.is_dir(parent):
            return f"Каталог не найден: {parent}"

        if self.is_dir(target):
            return f"Уже существует каталог с именем: {target}"

        self.files[target] = b""
        return None

    def copy_file(self, source, destination):
        """Копирует файл внутри VFS. Возвращает None или ошибку.

        - источник должен быть файлом;
        - если назначение — папка, файл копируется внутрь неё
          с тем же именем;
        - если назначение — не папка, оно считается новым именем файла.
        """
        src = self.absolute(source)
        dst = self.absolute(destination)

        if not self.is_file(src):
            return f"Файл не найден: {src}"

        # Если dst — папка, кладём файл внутрь с тем же именем
        if self.is_dir(dst):
            dst = posixpath.join(dst, posixpath.basename(src))

        parent = posixpath.dirname(dst)
        if not self.is_dir(parent):
            return f"Каталог не найден: {parent}"

        self.files[dst] = self.files[src]
        return None

    def load_from_zip(self, zip_path):
        """Загружает VFS из ZIP-файла (синоним init_from_zip)."""
        return self.init_from_zip(zip_path)