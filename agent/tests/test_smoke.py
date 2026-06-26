def test_package_imports_and_exposes_version():
    import jobpin_agent

    assert isinstance(jobpin_agent.__version__, str)
    assert jobpin_agent.__version__
