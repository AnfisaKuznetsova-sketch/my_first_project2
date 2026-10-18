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
        self.files = {}
        self.dirs = {"/"}
        self.cwd = "/"
        self.source = None


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


    def exists(self, path):
        """Проверяет, что путь есть в VFS (файл или папка)."""
        return path in self.files or path in self.dirs

    def is_dir(self, path):
        """Проверяет, что путь — это папка."""
        return path in self.dirs

    def is_file(self, path):
        """Проверяет, что путь — это файл."""
        return path in self.files

    def _child_files(self, prefix):
        """Возвращает имена файлов, лежащих непосредственно в prefix."""
        result = []
        for path in self.files:
            if not path.startswith(prefix):
                continue
            tail = path[len(prefix):]
            if "/" not in tail:
                result.append(tail)
        return result

    def _child_dirs(self, prefix, parent):
        """Возвращает имена подпапок, лежащих непосредственно в parent."""
        result = []
        for path in self.dirs:
            if path == parent or path == "/":
                continue
            if path in self.files:
                continue
            if not path.startswith(prefix):
                continue
            tail = path[len(prefix):]
            if "/" not in tail and tail:
                result.append(tail)
        return result

    def list_dir(self, path):
        """Возвращает содержимое папки: два списка (файлы, папки).

        Если путь не папка — возвращает (None, None).
        """
        if not self.is_dir(path):
            return None, None

        prefix = path.rstrip("/") + "/"
        files = self._child_files(prefix)
        dirs = self._child_dirs(prefix, path)
        return sorted(files), sorted(dirs)

    def read_file(self, path):
        """Читает файл из VFS. Возвращает (текст, ошибка).

        Текст декодируется как UTF-8 (с заменой некорректных байт).
        """
        if not self.is_file(path):
            return None, f"Файл не найден: {path}"
        data = self.files[path]
        return data.decode("utf-8", errors="replace"), None


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