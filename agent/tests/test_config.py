"""Tests for config + the .env loader.

EN —
Confirms ``_load_dotenv`` seeds unset variables from a ``.env`` file but never
overrides variables already present in the environment.
中文 —
确认 ``_load_dotenv`` 从 ``.env`` 文件为未设置的变量赋值，但绝不覆盖环境中已存在的变量。
"""
import os

import pytest

from jobpin_agent.core.config import CoreConfig, _load_dotenv


def test_load_dotenv_sets_unset_keys_and_does_not_override(tmp_path):
    """A .env value fills an unset var; a preset env var is left untouched.

    EN: K1 (unset) is populated from .env; K2 (preset) keeps its real value;
    comments/blank lines and surrounding quotes are handled.
    中文：K1（未设置）由 .env 填充；K2（已设置）保留其真实值；注释/空行与首尾引号被正确处理。
    """
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# a comment\n\nJOBPIN_TEST_K1=from_dotenv\nJOBPIN_TEST_K2=\"should-not-win\"\n",
        encoding="utf-8",
    )
    os.environ.pop("JOBPIN_TEST_K1", None)
    os.environ["JOBPIN_TEST_K2"] = "preset"
    try:
        _load_dotenv(env_file)
        assert os.environ["JOBPIN_TEST_K1"] == "from_dotenv"
        assert os.environ["JOBPIN_TEST_K2"] == "preset"  # setdefault did not override
    finally:
        os.environ.pop("JOBPIN_TEST_K1", None)
        os.environ.pop("JOBPIN_TEST_K2", None)


def test_encryption_flag_fails_loud_until_wired():
    """Setting ``encryption_enabled`` raises (no composition root wires it yet) — never silent plaintext.

    EN: A compliance-first product must not let an operator believe data is encrypted when the flag is
        inert; §1.9 makes it fail loud. Default (False) constructs fine.
    中文：合规优先的产品不能让运维以为数据已加密而标志实为空转；§1.9 让其失败即响。默认（False）可正常构造。
    """
    assert CoreConfig().encryption_enabled is False  # default constructs fine
    with pytest.raises(NotImplementedError):
        CoreConfig(encryption_enabled=True)
