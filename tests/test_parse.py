"""Тесты для парсера аргументов split_args."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "src"))

import firststage


class TestSplitArgs(unittest.TestCase):
    """Тесты функции split_args."""

    def test_simple(self):
        """Разбор простой строки без кавычек."""
        args, bad = firststage.split_args("ls -la file.txt")
        self.assertEqual(args, ["ls", "-la", "file.txt"])
        self.assertEqual(bad, "")

    def test_double_quotes(self):
        """Аргумент в двойных кавычках — единый токен."""
        args, bad = firststage.split_args('ls "my folder"')
        self.assertEqual(args, ["ls", "my folder"])

    def test_single_quotes(self):
        """Аргумент в одинарных кавычках — единый токен."""
        args, bad = firststage.split_args("cd 'Program Files'")
        self.assertEqual(args, ["cd", "Program Files"])

    def test_unclosed_double(self):
        """Незакрытая двойная кавычка — флаг ошибки."""
        args, bad = firststage.split_args('ls "незакрытая')
        self.assertEqual(bad, '"')

    def test_empty(self):
        """Пустая строка — пустой список слов."""
        args, bad = firststage.split_args("")
        self.assertEqual(args, [])


if __name__ == "__main__":
    unittest.main()