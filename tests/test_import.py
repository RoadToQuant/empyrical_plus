import pytest


class TestImport:

    def test_top_level_import(self):
        import empyrical_plus as ep
        assert hasattr(ep, "sharpe_ratio")
        assert hasattr(ep, "max_drawdown")
        assert hasattr(ep, "annual_return")
        assert hasattr(ep, "alpha")
        assert hasattr(ep, "beta")
        assert hasattr(ep, "cum_returns")
        assert hasattr(ep, "perf_attrib")

    def test_submodule_import(self):
        import importlib
        from empyrical_plus import stats
        from empyrical_plus import utils
        from empyrical_plus import periods
        perf_attrib_module = importlib.import_module('empyrical_plus.perf_attrib')
        assert hasattr(stats, "sharpe_ratio")
        assert hasattr(utils, "roll")
        assert hasattr(periods, "DAILY")
        assert hasattr(perf_attrib_module, "perf_attrib")
