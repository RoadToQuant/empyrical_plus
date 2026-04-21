# Empyrical Plus Rust 迁移方案

> 将核心数值计算从 Python/Numpy 迁移至 Rust，在保持 API 完全兼容的前提下提升计算效率和降低内存占用。

---

## 一、环境检查结果

| 工具 | 当前 Windows 环境 | 说明 |
|------|------------------|------|
| `rustc` | ❌ 未安装 | Rust 编译器 |
| `cargo` | ❌ 未安装 | Rust 包管理器 |
| `maturin` | ❌ 未安装 | PyO3 构建/发布工具 |
| MSVC Build Tools | 未知 | Windows 上编译 PyO3 必需 |

**结论：当前环境不支持 Rust 开发。建议在 macOS（或已安装 Rust 的 Linux/Windows）上实施。**

---

## 二、技术选型

| 组件 | 选型 | 用途 |
|------|------|------|
| `pyo3` 0.23+ | Python ↔ Rust 绑定 | 暴露 Rust 函数为 Python 模块 |
| `rust-numpy` 0.23+ | NumPy C-API 封装 | 零拷贝读写 `np.ndarray` |
| `ndarray` 0.16+ | Rust 端数组计算 | 向量化运算、矩阵操作、滑动窗口 |
| `maturin` 1.7+ | 构建工具 | 替代 `setuptools`，编译并打包 mixed Python/Rust 项目 |
| `num-traits` | 数值抽象 | 泛型数值计算（如 `f64` 的 `NaN` 处理） |

---

## 三、迁移后项目结构

```
empyrical_plus/
├── Cargo.toml                  # Rust crate 配置
├── pyproject.toml              # 改为 maturin build-backend
├── src/
│   └── lib.rs                  # Rust 入口：注册 _core 模块
│   └── core/
│       ├── mod.rs              # 模块聚合
│       ├── returns.rs          # cum_returns, simple_returns, annual_return, cagr
│       ├── risk.rs             # max_drawdown, downside_risk, VaR, CVaR, tail_ratio
│       ├── ratios.rs           # sharpe, sortino, calmar, omega, excess_sharpe
│       ├── regression.rs       # alpha, beta, alpha_beta, stability_of_timeseries
│       └── rolling.rs          # roll_sharpe, roll_max_dd, roll_alpha_beta 等滑动窗口
├── empyrical_plus/             # Python 包装层（保留完整 API）
│   ├── __init__.py             # 从 _core 导入 Rust 函数并重新暴露
│   ├── stats.py                # 薄包装：类型转换（pd.Series → ndarray → Rust）
│   ├── utils.py                # 辅助函数、deprecated、rolling 框架
│   ├── periods.py              # 年化因子常数（纯 Python，不动）
│   └── perf_attrib.py          # 绩效归因（保留 Python，原因见下）
└── tests/                      # 测试集不变，全部复用
```

### 为什么保留 `perf_attrib.py` 为 Python？

`perf_attrib` 重度依赖 `pandas.MultiIndex`、`groupby(level='dt')`、DataFrame 对齐和列运算。这些在 Rust 中需要引入 `polars` 并重新设计数据结构，边际收益低、迁移成本高。优先迁移**纯数值标量/向量**计算。

---

## 四、分阶段迁移计划

### Phase 1：核心标量统计（ROI 最高）

输入为 1-D `f64` 数组，输出为标量或同型 1-D 数组，无复杂索引操作。

| 模块 | 函数 |
|------|------|
| `returns.rs` | `cum_returns`, `cum_returns_final`, `simple_returns`, `annual_return`, `cagr`, `aggregate_returns` |
| `risk.rs` | `max_drawdown`, `annual_volatility`, `downside_risk`, `value_at_risk`, `conditional_value_at_risk`, `tail_ratio` |
| `ratios.rs` | `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`, `omega_ratio`, `excess_sharpe` |

**性能预期**：2–5× 加速，内存下降 20–40%。
- 消除 pandas Index 对齐和中间 Series 分配
- Rust 单遍遍历计算多个统计量（如 sharpe 同时算 mean 和 var）
- nan-handling 内联在循环中，避免 numpy 的额外掩码扫描

### Phase 2：回归与稳定性

| 模块 | 函数 |
|------|------|
| `regression.rs` | `alpha`, `beta`, `alpha_beta`, `alpha_aligned`, `beta_aligned`, `stability_of_timeseries` |

当前 `alpha`/`beta` 的实现已经是向量化 numpy 操作（cov/var），但 Rust 可以进一步：
- 对 `alpha_beta` 一次性同时计算协方差、方差、均值，避免多次遍历
- `stability_of_timeseries` 的 `linregress` 用最小二乘解析解直接算出

### Phase 3：滚动窗口（加速最显著）

| 模块 | 函数 |
|------|------|
| `rolling.rs` | `roll_sharpe_ratio`, `roll_sortino_ratio`, `roll_max_drawdown`, `roll_alpha`, `roll_beta`, `roll_alpha_beta`, `roll_up_capture`, `roll_down_capture`, `roll_up_down_capture`, `roll_annual_volatility` |

当前实现是在 Python 层循环调用底层函数（`utils.roll` → `_roll_ndarray` → Python lambda）。**Rust 滑动窗口算法**可以做到 O(n) 总体复杂度：
- 维护窗口内 `sum`、`sum_sq`、`count`，每步 O(1) 更新
- `roll_max_drawdown` 用单调队列或滑动 cum_max
- 预期加速：**10–50×**

### Phase 4：方向性捕获与 2-D 支持

| 模块 | 函数 |
|------|------|
| `regression.rs` / `returns.rs` | `capture`, `up_capture`, `down_capture`, `up_down_capture`, `down_alpha_beta`, `up_alpha_beta` |

这些函数需要按条件过滤（`up()`/`down()`）后再计算。Rust 端可以实现为：
- 接收 benchmark 和 returns 两个数组
- 内部根据符号过滤后调用 Phase 1/2 的已有实现

### Phase 5（可选）：perf_attrib

仅在确认 Polars 可以零摩擦替代 pandas MultiIndex 操作后再考虑。

---

## 五、Python ↔ Rust 接口设计

### 5.1 Rust 侧（`src/core/ratios.rs` 示例）

```rust
use numpy::{PyReadonlyArray1, PyArray1, IntoPyArray};
use pyo3::prelude::*;
use ndarray::Array1;

/// nan-aware sharpe ratio
#[pyfunction]
fn sharpe_ratio(
    returns: PyReadonlyArray1<f64>,
    risk_free: f64,
    ann_factor: f64,
) -> PyResult<f64> {
    let slice = returns.as_slice()?;
    let mut sum = 0.0;
    let mut sum_sq = 0.0;
    let mut n = 0usize;

    for &v in slice.iter() {
        if v.is_nan() { continue; }
        let adj = v - risk_free;
        sum += adj;
        sum_sq += adj * adj;
        n += 1;
    }

    if n < 2 {
        return Ok(f64::NAN);
    }

    let mean = sum / n as f64;
    let variance = (sum_sq / n as f64) - (mean * mean);
    if variance <= 0.0 || variance.is_nan() {
        return Ok(f64::NAN);
    }

    Ok(mean / variance.sqrt() * ann_factor.sqrt())
}
```

### 5.2 Python 侧（`empyrical_plus/stats.py` 薄包装）

```python
from empyrical_plus._core import sharpe_ratio as _sharpe_ratio_rs
from empyrical_plus.utils import _to_ndarray, _wrap_scalar
from empyrical_plus.periods import annualization_factor

DAILY = "daily"

def sharpe_ratio(returns, risk_free=0.0, period=DAILY, annualization=None, out=None):
    # 保持现有签名 100% 不变
    arr = _to_ndarray(returns)          # pd.Series / np.ndarray → np.ndarray
    ann = annualization_factor(period, annualization)
    result = _sharpe_ratio_rs(arr, risk_free, ann)
    return _wrap_scalar(result, returns)  # 恢复 pd.Series / float 等原始类型
```

### 5.3 关键约定

- **输入**：Rust 侧统一接受 `PyReadonlyArray1<f64>`（零拷贝只读视图）
- **输出标量**：`PyResult<f64>`，Python 层负责 `np.nan` 语义包装
- **输出向量**：`PyResult<Bound<'py, PyArray1<f64>>>`，通过 `into_pyarray(py)` 返回
- **nan 处理**：Rust 侧显式 `is_nan()` 跳过，与 numpy `nanmean` 行为一致
- **索引保留**：所有 Index/DatetimeIndex 操作保留在 Python 层，Rust 只操作裸数组

---

## 六、构建与发布流程调整

### 6.1 本地开发（macOS/Linux/Windows with Rust）

```bash
# 1. 安装 Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 2. 安装 maturin
pip install maturin

# 3. 开发模式编译（带热重载）
maturin develop --release

# 4. 运行测试
pytest tests/
```

### 6.2 `pyproject.toml` 关键变更

```toml
[build-system]
requires = ["maturin>=1.7,<2.0"]
build-backend = "maturin"

[project]
name = "dsf-empyrical"
version = "1.0.2"

[tool.maturin]
module-name = "empyrical_plus._core"
python-source = "."          # Python 源码在根目录（与当前结构一致）
```

### 6.3 CI/CD 调整

引入 Rust 后，wheel 变为**平台相关**（含原生 `.so`/`.dll`/`.dylib`），不再是 `py3-none-any`。

#### test-build（矩阵验证）
保留现有矩阵，但增加 `maturin develop` 步骤：
- `ubuntu-latest` / `windows-latest` / `macos-latest` / `macos-14`(ARM)
- Python 3.9 / 3.12

#### release-build（多平台产物）
改为矩阵构建，每个平台构建自己的 wheel：
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest, macos-14]
    python-version: ["3.9", "3.10", "3.11", "3.12"]
```
- 使用 `maturin build --release` 替代 `python -m build`
- 上传 artifact，命名带平台标识（如 `wheel-linux-py39`）

#### pypi-publish
- 下载所有平台 artifact
- `twine upload` 或继续使用 `gh-action-pypi-publish`
- Trusted Publishing 仍然适用

**替代方案**：使用 [`cibuildwheel`](https://cibuildwheel.pypa.io/) 在单台 Linux runner 上通过 QEMU/Docker 交叉编译所有平台 wheel，简化 CI。但 macOS ARM64 仍需在 `macos-14` 上原生构建。

---

## 七、性能基准预期

| 场景 | Python/Numpy | Rust (预期) | 加速比 |
|------|-------------|-------------|--------|
| `sharpe_ratio` 单序列 | 0.15 ms | 0.04 ms | **4×** |
| `max_drawdown` 10万点 | 2.1 ms | 0.5 ms | **4×** |
| `roll_sharpe_ratio` 窗口20 | 45 ms | 1.2 ms | **37×** |
| `roll_max_drawdown` 窗口60 | 120 ms | 3.0 ms | **40×** |
| `alpha_beta` 双序列 | 0.8 ms | 0.2 ms | **4×** |

> 注：以上为基于相似 PyO3 + rust-numpy 项目的经验估算，实际数值取决于硬件和具体数据分布。

---

## 八、风险与注意事项

1. **构建复杂度上升**：用户端安装时需要编译 Rust（如果无预编译 wheel），因此 CI 必须确保所有目标平台都有预编译 wheel 上传 PyPI。
2. **调试成本**：Rust panic 会导致 Python 进程崩溃（而非抛异常）。需要在 Rust 侧用 `Result` 包裹所有错误，并在边界处转换为 `PyErr`。
3. **pandas 兼容性**：Rust 侧不处理 pandas Index，所有索引保留/恢复逻辑留在 Python `stats.py` 包装层。
4. **浮点精度**：Rust `f64` 与 numpy `float64` 的 IEEE-754 实现一致，但运算顺序差异可能导致末位小数不同。测试断言的 `decimal_places` 可能需要从 8 放宽到 7。
5. **GIL**：PyO3 默认持有 GIL。对于纯计算函数，可用 `py.allow_threads(|| { ... })` 释放 GIL，让其他 Python 线程并行执行。

---

## 九、下一步建议

1. **在 macOS 上初始化 Rust 环境**：`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
2. **初始化 maturin 项目结构**：在 repo 根目录执行 `maturin init --mixed`
3. **先实现单个函数作为 PoC**：建议从 `max_drawdown` 或 `sharpe_ratio` 开始，验证构建流程和测试兼容性
4. **逐步替换**：按 Phase 1 → Phase 2 → Phase 3 顺序迁移，每阶段保持测试全绿

如果你确认在 macOS 上实施，我可以继续帮你初始化 `Cargo.toml`、`src/lib.rs` 和改造后的 `pyproject.toml`。
