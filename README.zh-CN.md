# KLine Kronos Suite（`v1.0.1` · 金融高频 K 线清洗、重采样与 Kronos 微调推演工作台）

[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/16679/badge)](https://www.bestpractices.dev/projects/16679)
[![CI & Coverage Gate](https://github.com/Ziqi/KLine-Kronos-Suite/actions/workflows/ci.yml/badge.svg)](https://github.com/Ziqi/KLine-Kronos-Suite/actions/workflows/ci.yml)
[![CodeQL SAST](https://github.com/Ziqi/KLine-Kronos-Suite/actions/workflows/codeql.yml/badge.svg)](https://github.com/Ziqi/KLine-Kronos-Suite/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/Ziqi/KLine-Kronos-Suite/badge)](https://scorecard.dev/viewer/?uri=github.com/Ziqi/KLine-Kronos-Suite)
[![SLSA 3](https://slsa.dev/images/gh-badge-level3.svg)](https://github.com/Ziqi/KLine-Kronos-Suite/attestations)
[![REUSE Compliant](https://img.shields.io/badge/REUSE-3.3%20compliant-brightgreen)](./REUSE.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

> **[English (`README.md`)](./README.md)** | **简体中文**

围绕金融时序基础模型 **[Kronos](https://github.com/shiyu-coder/Kronos)** 打造的端到端 **1 分钟高频行情获取清洗 → 交易时段对齐 5 分钟重采样 → 数据质检打包 → 双阶段微调监控 → 自回归推演画图** 模块化工具套件（同时提供 **零第三方依赖纯标准库 CLI** 与 **`ttkbootstrap` 暗金桌面工作台**）。

---

## 解决的核心工程痛点

1. **日内微结构噪音自动净化**：自动去重并剔除 `13:00:00` 午盘边界噪点与 `15:01–15:31` 盘后冗余帧，缺失 `15:00:00` 收盘帧时自动按最后成交价零量补齐。
2. **严格的右闭合 `1m -> 5m` 时间窗对齐**：采用确定性 `closed='right', label='right'` 规则（`09:31..09:35` 聚合标记为 `09:35`），杜绝未来函数与跨段错位，全面兼容 `pandas 2.x / 3.x`（`'5min'`）与纯标准库极速模式。
3. **张量入库前严苛质检（QA Gate）与属性模糊测试**：自动拦截缺列、空值、`high < low` 价格倒挂与非单调时间戳，内置 2,000 轮随机化/Atheris 属性模糊测试（`tests/fuzz_kline_pipeline.py`），并支持生成带 `SHA-256` 校验的 JSON 数据集清单。
4. **贴合 A 股交易日历的多步推演对齐**：推演步进器自动跨越 `11:30–13:00` 午休、隔夜休市与周末，执行截面 Z-Score 归一化（`clip[-5, 5]`）与逆变换还原真实价格刻度。

---

## 30 秒零依赖命令行快速体验

无需安装任何第三方库，直接使用 Python 3.10+ 即可在内置合成样本（`examples/sample_1m_ohlcv.csv`）上跑通完整数据链路：

```bash
git clone https://github.com/Ziqi/KLine-Kronos-Suite.git
cd KLine-Kronos-Suite

# 1. 清洗 1 分钟原始 K 线并补齐 15:00 收盘帧
python3 -m kline_kronos clean ./examples/sample_1m_ohlcv.csv --output /tmp/sample_1m_clean.csv

# 2. 按右闭合标准重采样为 5 分钟 K 线
python3 -m kline_kronos resample /tmp/sample_1m_clean.csv --out-dir /tmp/out_5m

# 3. 执行完整性、上下界与时间戳单调性质检
python3 -m kline_kronos audit /tmp/out_5m/sample_5m_clean.csv --min-rows 2

# 4. 生成确定性 SHA-256 数据集资产清单
python3 -m kline_kronos manifest /tmp/out_5m --output /tmp/dataset_manifest.json --min-rows 2
```

---

## 五阶段模块与工程路线图

- **[`kline_kronos/`](./kline_kronos/)**：零依赖核心算法库与无头服务器 CLI（`clean` / `resample` / `audit` / `manifest`）。
- **[`01_extract/`](./01_extract/)**：1 分钟高频 K 线增量采集器与桌面工作站（通过环境变量 `MIANA_TOKEN` 传入接口凭证）。
- **[`02_resample/`](./02_resample/)**：`1m -> 5m` 批量多进程重采样桌面终端。
- **[`03_slicer/`](./03_slicer/)**：5 分钟 CSV 批量体检与 Kronos `.pkl` 训练字典打包器。
- **[`04_trainer_gui/`](./04_trainer_gui/)**：双阶段（`Tokenizer` + `Predictor`）隔离虚拟环境训练进程监控台（支持 `KRONOS_HOME` 环境变量）。
- **[`05_predictor_gui/`](./05_predictor_gui/)**：截面归一化推演与 K 线轨迹可视化终端。
- **[`docs/ROADMAP.md`](./docs/ROADMAP.md)**：`v1.1` Parquet/SafeTensors 后端、`v1.2` 港美股/加密多市场日历与 `v2.0` 本地加速推演路线图。

## 质量门禁与开源协议

- 本地执行 `python3 ./tests/test_pipeline_core.py --min-coverage 85 && python3 ./tests/fuzz_kline_pipeline.py --iterations 2000` 即可运行单元测试、2,000 轮模糊测试、AST 安全扫描与 `>=85%` 语句覆盖率门禁。
- 本项目基于 [MIT License](./LICENSE) 开源，欢迎在 [GitHub Discussions](https://github.com/Ziqi/KLine-Kronos-Suite/discussions) 交流量化数据工程与 Kronos 微调实践。
