import unittest
from click.testing import CliRunner

from metayaml.cli import *

class TestMetayaml(unittest.TestCase):
    def test_trivial(x):
        assert 1 + 1 == 2

    def test_parse_string(x):
        assert parse_string("foo") == "foo"
        assert parse_string("True") == True
        assert parse_string("1.1") == 1.1
    
    def test_validate(x):
        runner = CliRunner()
        result = runner.invoke(validate, ["example/EU/meta.yml", "example/schema.yml"])
        assert result.exit_code == 0

        result = runner.invoke(validate, ["example/EU/de.txt.meta.yml", "example/schema.yml"])
        assert result.exit_code == 1