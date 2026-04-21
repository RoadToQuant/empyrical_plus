# AGENTS.md — Empyrical Plus

> This file contains project-specific context for AI coding agents.
> The project uses English for all code, docstrings, and documentation.

---

## Project Overview

`empyrical_plus` is a Python library for financial performance and risk statistics. It is a fork/extension of [Quantopian's `empyrical`](https://github.com/quantopian/empyrical) and provides common metrics used in quantitative finance, such as Sharpe ratio, Sortino ratio, max drawdown, alpha, beta, VaR, CVaR, and performance attribution.

- **Package name**: `empyrical_plus`
- **PyPI distribution name**: `dsf-empyrical`
- **Current version**: `1.0.2` (hardcoded in `pyproject.toml` and `empyrical_plus/__init__.py`)
- **Python support**: `>=3.9`
- **License**: MIT (source files retain original Apache 2.0 headers from Quantopian)

---

## Technology Stack

| Component | Details |
|-----------|---------|
| Language | Python 3.9+ |
| Core deps | `numpy>=1.21.6`, `pandas>=1.3.5`, `scipy` |
| Build tool | `setuptools` via `pyproject.toml` (`setup.py` kept as minimal compatibility shell) |
| CI/CD | GitHub Actions (`.github/workflows/release.yml`) |
| Test runner | `pytest` (configured in `pyproject.toml`) |

There is **no** `tox.ini`, `Makefile`, or `pytest.ini`.

---

## Project Structure

```
empyrical_plus/
├── empyrical_plus/           # Main package
│   ├── __init__.py           # Public API exports + __version__ + __all__
│   ├── stats.py              # Core statistical/risk functions (~2170 lines)
│   ├── utils.py              # Rolling-window helpers, nan-aware wrappers, array utilities
│   ├── periods.py            # Time-period constants and annualization factors
│   ├── perf_attrib.py        # Performance attribution (factor exposure decomposition)
│   └── _version.py           # Hard-coded __version__
├── tests/
│   ├── __init__.py
│   ├── test_stats.py         # Unit tests for stats.py (~1740 lines)
│   ├── test_perf_attrib.py   # Unit tests for perf_attrib.py
│   ├── test_import.py        # Smoke tests for top-level API exposure
│   └── test_version.py       # Version consistency check
├── pyproject.toml            # Package metadata, dependencies, pytest config
├── setup.py                  # Minimal compatibility shell
├── requirements.txt          # Pins numpy/pandas; uses Aliyun PyPI mirror
├── README.md
└── .github/workflows/release.yml
```

### Module Breakdown

- **`stats.py`** — The bulk of the library. Implements:
  - Return metrics: `cum_returns`, `annual_return`, `cagr`, `aggregate_returns`
  - Risk metrics: `max_drawdown`, `annual_volatility`, `downside_risk`, `value_at_risk`, `conditional_value_at_risk`, `tail_ratio`
  - Ratios: `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`, `omega_ratio`, `excess_sharpe`
  - Regression metrics: `alpha`, `beta`, `alpha_beta`, `stability_of_timeseries`
  - Rolling variants: `roll_alpha`, `roll_beta`, `roll_sharpe_ratio`, `roll_max_drawdown`, etc.
  - Capture metrics: `up_capture`, `down_capture`, `up_down_capture`
  - Heuristics: `beta_fragility_heuristic`, `gpd_risk_estimates`

- **`utils.py`** — Helper infrastructure:
  - `roll()` / `_roll_ndarray()` / `_roll_pandas()` for rolling-window calculations
  - `up()` / `down()` for filtering positive/negative benchmark periods
  - `rolling_window()` using `numpy.lib.stride_tricks.as_strided`
  - Optional `bottleneck` acceleration for nan-aware operations (`nanmean`, `nanstd`, etc.)

- **`periods.py`** — Constants: `DAILY`, `WEEKLY`, `MONTHLY`, `QUARTERLY`, `YEARLY`, plus `ANNUALIZATION_FACTORS`.

- **`perf_attrib.py`** — Factor-based performance attribution. Given portfolio positions, factor returns, and factor loadings, decomposes returns into `common_returns`, `specific_returns`, `tilt_returns`, and `timing_returns`.

---

## Build, Install, and Release

### Local install
```bash
pip install -r requirements.txt
pip install -e ".[test]"
```

### Build wheel/sdist
```bash
python -m build
```

### Release process
- Pushing to the `release` branch, or publishing a GitHub Release, triggers `.github/workflows/release.yml`.
- The workflow uses a three-stage design:
  1. **test-build**: Matrix validation across `ubuntu-latest`, `windows-latest`, `macos-latest` × Python 3.9/3.12. Builds package and runs tests.
  2. **release-build**: Builds the canonical sdist + wheel on `ubuntu-latest` + Python 3.9, uploads as a single artifact (`release-dists`).
  3. **pypi-publish**: Downloads the artifact and publishes to PyPI via **Trusted Publishing** (OIDC). No long-lived tokens are stored in the repository.

---

## Testing

### Running tests
```bash
pytest tests/
```

### Test organization
- `TestImport` — smoke tests for package import and top-level API.
- `test_version` — verifies `__version__` matches `pyproject.toml`.
- `BaseTestCase` — custom `unittest.TestCase` with `assert_indexes_match`.
- `TestStats` / `TestStatsArrays` / `TestStatsIntIndex` — core stat function tests.
- `TestHelpers` — utility function tests.
- `Test2DStats` / `Test2DStatsArrays` — 2-D array tests.
- `PerfAttribTestCase` — performance attribution tests.

---

## Code Style Guidelines

- Use **numpy-style docstrings** (Parameters, Returns, Examples).
- Keep original **Apache 2.0 license headers** on files derived from Quantopian's `empyrical`.
- `__init__.py` is marked `# flake8: noqa` because it performs broad star-like imports.
- Prefer `np.ndarray` and `pd.Series` inputs; functions should return the same type as the input where possible.

---

## Security Considerations

- The project has no network surface area; it is a pure computational library.
- `requirements.txt` uses an Aliyun PyPI mirror (`-i https://mirrors.aliyun.com/pypi/simple/`). Ensure this is acceptable in your environment before installing.
- CI uses **Trusted Publishing** (OIDC) to authenticate with PyPI. No `PYPI_TOKEN` secret is stored in GitHub.

---

## Agent Notes

- When adding new public functions, export them in `empyrical_plus/__init__.py` and add to `__all__`.
- When changing dependencies, update `pyproject.toml` (both `[project] dependencies` and `[project.optional-dependencies]`).
- For version bumps, update both `pyproject.toml` and `empyrical_plus/__init__.py`.
- Branch strategy:
  - `master` — main development branch (no protection required).
  - `release` — triggers the PyPI publish workflow.
