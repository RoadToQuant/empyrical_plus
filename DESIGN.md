# EmpyricalPlus 模组设计与工程实践

> 本文档记录 `empyrical_plus` 的工程设计与发布实践，涵盖包管理、CI/CD、测试策略及安全实践。作为同类 Python 科学计算/量化工具箱的模板参考。

---

## 一、设计哲学

- **对外极简**：用户只需 `import empyrical_plus as ep`，常用函数全部暴露在包顶层。
- **对内清晰**：子模块按职责分层（stats → utils → periods → perf_attrib），避免循环依赖。
- **发布安全**：零长期凭证（Trusted Publishing），多平台矩阵验证但发布产物唯一。
- **现代 Python**：仅支持 Python 3.9+，彻底移除 Python 2 兼容层。

---

## 二、目录与模块划分

```
empyrical_plus/
├── __init__.py      # 版本号 + 顶层 API 统一暴露 + __all__
├── stats.py         # 核心统计/风险函数
├── utils.py         # 滚动窗口、nan-aware 包装器、数组工具
├── periods.py       # 时间周期常数和年化因子
├── perf_attrib.py   # 绩效归因（因子暴露分解）


tests/
├── test_stats.py         # stats.py 单元测试
├── test_perf_attrib.py   # perf_attrib.py 单元测试
├── test_import.py        # 包导入与顶层 API 存在性检查
└── test_version.py       # 版本号一致性检查

根目录配置:
├── pyproject.toml              # 包配置、依赖、pytest 配置
├── requirements.txt            # 保留参考（阿里云镜像）
├── .github/workflows/release.yml  # CI/CD 发布流程
├── DESIGN.md                   # 本文件
├── AGENTS.md                   # Agent 上下文
├── CLAUDE.md                   # LLM 编码规范
└── README.md                   # 面向用户的使用文档
```

---

## 三、包管理设计

### 3.1 pyproject.toml 结构

- **`[build-system]`**：`setuptools>=61.0` + `wheel`，兼容 `uv` / `pip` / `build`。
- **`[project]`**：
  - `name` 使用 **PyPI 分发名** `dsf-empyrical`。
  - 导入名由 `[tool.setuptools] packages` 单独指定为 `empyrical_plus`，两者解耦。
  - `license` 使用 SPDX 短标识符 `"MIT"`。
- **`[project.optional-dependencies]`**：`test` extra 包含 `parameterized` 和 `pytest`。
- **`[tool.pytest.ini_options]`**：原生集成 pytest 配置，无需额外 `pytest.ini`。

### 3.2 版本号管理

- 采用**双点硬编码**：`pyproject.toml` 的 `project.version` 与 `empyrical_plus/__init__.py` 保持一致。
- 不引入 `setuptools_scm` 或 `versioneer`，避免干净环境构建失败。

### 3.3 顶层 API 暴露

`__init__.py` 从各子模块显式导入最常用函数，并更新 `__all__`：

```python
from .stats import sharpe_ratio, max_drawdown, ...
from .perf_attrib import perf_attrib, compute_exposures
```

---

## 四、Git 工作流设计

### 4.1 分支策略

| 分支 | 用途 | 保护规则 |
|------|------|----------|
| `master` | 主开发分支 | 无保护，直接 push |
| `release` | 触发正式发布构建 | 按需保护 |

### 4.2 Commit 规范

采用简洁的语义化前缀：
- `refactor:` 重构（版本控制、模块重命名、API 暴露）
- `ci:` CI/CD 相关（workflow 调整、构建修复）
- `chore:` 工程杂项（文档迁移）
- `fix:` 功能修复

---

## 五、发布流程设计（GitHub Actions）

### 5.1 触发条件

```yaml
on:
  push:
    branches:
      - release
  release:
    types: [published]
```

- **日常开发 push 到 master**：不触发发布。
- **正式发布**： push 到 `release` 分支，或手动在 GitHub 上创建 Release。

### 5.2 三阶段 Job 设计

#### Stage 1: test-build（矩阵验证）

```yaml
strategy:
  fail-fast: false
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    python-version: ["3.9", "3.12"]
```

- 在 6 个组合上分别执行 `python -m build` + `twine check dist/*` + `pytest tests/`。
- **不上传 artifact**，仅验证构建正确性与跨平台兼容性。
- 纯 Python 包的平台标签为 `py3-none-any`，无需多平台分别构建 wheel。

#### Stage 2: release-build（唯一发布产物）

- 仅在 `ubuntu-latest` + Python 3.9 上构建一次。
- 产物（wheel + sdist）通过 `actions/upload-artifact@v4` 上传，artifact name 唯一（`release-dists`）。
- 依赖 `test-build` 全部成功，避免构建失败时仍尝试发布。

#### Stage 3: pypi-publish（发布到 PyPI）

```yaml
permissions:
  id-token: write
environment:
  name: pypi
```

- 使用 `actions/download-artifact@v4` 下载单一 artifact，**不使用 `merge-multiple`**，避免同名文件覆盖导致 `BadZipFile`。
- 使用 `pypa/gh-action-pypi-publish@release/v1`，**不设置 `password`**，强制走 Trusted Publishing (OIDC)。

---

## 六、安全实践

### 6.1 Trusted Publishing（零长期凭证）

**原理**：GitHub Actions 向 GitHub OIDC 服务商申请短期 JWT（内含仓库、workflow、分支、environment 声明），PyPI 验证声明后颁发临时上传令牌（约 15 分钟有效）。

**优势**：
- 仓库内不存在任何 `PYPI_TOKEN` secret。
- 临时令牌自动过期，泄露窗口极小。
- 可精确绑定到具体仓库 + workflow + environment。

---

## 七、测试策略

- **框架**：pytest（替代原有的 unittest discover）。
- **数据**：全部使用 `numpy`/`pandas` 生成模拟数据，零外部依赖。
- **结构**：`test_import.py` / `test_version.py` 作为冒烟测试，确保包安装后基本可用。
- **兼容性**：CI 矩阵覆盖 Windows/Linux/macOS，确保纯 Python 包在多平台均可正常安装和运行。
