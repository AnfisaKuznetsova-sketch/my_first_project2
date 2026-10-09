"""Тесты для парсера аргументов split_args."""
import os
import sys
import unittest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "src")
)

from firststage import split_args  # noqa: E402


class TestSplitArgs(unittest.TestCase):
    def test_simple(self):
        args, bad = split_args("ls -la file.txt")
        self.assertEqual(args, ["ls", "-la", "file.txt"])
        self.assertEqual(bad, "")

    def test_double_quotes(self):
        args, bad = split_args('ls "my folder"')
        self.assertEqual(args, ["ls", "my folder"])

    def test_unclosed_double(self):
        args, bad = split_args('ls "незакрытая')
        self.assertEqual(bad, '"')

    def test_empty(self):
        args, bad = split_args("")
        self.assertEqual(args, [])


if __name__ == "__main__":
    unittest.main()