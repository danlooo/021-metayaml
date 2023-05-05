import unittest
from metayaml import core

class TestMetayaml(unittest.TestCase):
    def test_trivial(x):
        assert 1 + 1 == 2

    def test_sandbox(self):
        assert core.meta_add(1, 1) == 2