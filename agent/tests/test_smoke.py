"""Smoke test — the package imports and exposes a version.

EN —
The most basic guard: if this fails, the package layout or environment is broken.
中文 —
最基本的护栏：若此测试失败，说明包布局或环境已损坏。
"""


def test_package_imports_and_exposes_version():
    """Importing the package yields a non-empty string ``__version__``.

    EN: Verifies the package is importable and ``__version__`` is a non-empty str.
    中文：验证包可导入且 ``__version__`` 为非空字符串。
    """
    import jobpin_agent

    assert isinstance(jobpin_agent.__version__, str)
    assert jobpin_agent.__version__
