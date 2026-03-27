"""TEST-6: Edge-case tests for tps_cita_check.env_utils.load_dotenv."""
from __future__ import annotations

import os

import pytest

from tps_cita_check.env_utils import load_dotenv

# Remove any test keys from the environment before / after each test.
_TEST_KEYS = ["_TPS_TEST_A", "_TPS_TEST_B", "_TPS_TEST_C", "_TPS_TEST_OFFICES"]


@pytest.fixture(autouse=True)
def _clean_env():
    for k in _TEST_KEYS:
        os.environ.pop(k, None)
    yield
    for k in _TEST_KEYS:
        os.environ.pop(k, None)


def _write_env(tmp_path, content: str):
    p = tmp_path / ".env"
    p.write_text(content)
    return str(p)


def test_standard_key_value(tmp_path):
    _write_env(tmp_path, "_TPS_TEST_A=hello\n_TPS_TEST_B=world\n")
    load_dotenv(str(tmp_path / ".env"))
    assert os.environ["_TPS_TEST_A"] == "hello"
    assert os.environ["_TPS_TEST_B"] == "world"


def test_double_quoted_value(tmp_path):
    _write_env(tmp_path, '_TPS_TEST_A="value with spaces"\n')
    load_dotenv(str(tmp_path / ".env"))
    assert os.environ["_TPS_TEST_A"] == "value with spaces"


def test_single_quoted_value(tmp_path):
    _write_env(tmp_path, "_TPS_TEST_A='single quoted'\n")
    load_dotenv(str(tmp_path / ".env"))
    assert os.environ["_TPS_TEST_A"] == "single quoted"


def test_comment_lines_ignored(tmp_path):
    _write_env(tmp_path, "# this is a comment\n_TPS_TEST_A=valid\n")
    load_dotenv(str(tmp_path / ".env"))
    assert os.environ["_TPS_TEST_A"] == "valid"


def test_empty_lines_ignored(tmp_path):
    _write_env(tmp_path, "\n\n_TPS_TEST_A=present\n\n")
    load_dotenv(str(tmp_path / ".env"))
    assert os.environ["_TPS_TEST_A"] == "present"


def test_value_with_equals_sign(tmp_path):
    """Values containing '=' should be preserved (partition stops at first '=')."""
    _write_env(tmp_path, "_TPS_TEST_A=foo=bar\n")
    load_dotenv(str(tmp_path / ".env"))
    assert os.environ["_TPS_TEST_A"] == "foo=bar"


def test_pipe_delimited_offices(tmp_path):
    _write_env(tmp_path, "_TPS_TEST_OFFICES=Office A|Office B|Office C\n")
    load_dotenv(str(tmp_path / ".env"))
    assert os.environ["_TPS_TEST_OFFICES"] == "Office A|Office B|Office C"


def test_missing_file_no_error(tmp_path):
    """load_dotenv should silently ignore a missing .env file."""
    load_dotenv(str(tmp_path / "nonexistent.env"))  # should not raise
    assert "_TPS_TEST_A" not in os.environ


def test_existing_env_not_overwritten(tmp_path):
    """os.environ.setdefault — pre-existing keys must NOT be overwritten."""
    os.environ["_TPS_TEST_A"] = "original"
    _write_env(tmp_path, "_TPS_TEST_A=new_value\n")
    load_dotenv(str(tmp_path / ".env"))
    assert os.environ["_TPS_TEST_A"] == "original"
