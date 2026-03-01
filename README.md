# KLine Kronos Suite 💻📈

**KLine Kronos Suite** 是一套端到端、全链路的 A 股（及全市场）高频金融时序数据处理与特征提纯矩阵。专为 **Kronos (by shiyu-coder)** 等大语言/序列模型量身打造的“数据源泉”。本套件将原始的分钟级金融数据，完美转化为适用于 Kronos 时序预测模型的标准格式。

整个 Suite 包含五大核心微型基站，遵循严格的 **"Flat Dark Gold (极客暗金)"** 设计美学和极客交互理念：

## 🚀 The Quintet (核心五星矩阵)

本项目采用子模块 (Git Submodules) 的形式聚合。点击下方各个独立工程查看具体源码与说明：

### 1. [1-KLine-Extract](https://github.com/Ziqi/1-KLine-Extract)
- **职能**: 最前线的物理爬虫雷达。
- **机制**: 用内置的军工级防封杀引擎和剪贴板自动嗅探，并发拉取全市场 1 分钟颗粒度 K 线。
- **阶段**: `Text -> 1m .csv`

### 2. [2-KLine-Resample](https://github.com/Ziqi/2-KLine-Resample)
- **职能**: 降噪与重组基座。
- **机制**: 严格遵循 A 股时间线属性（`closed='right', label='right'`），将细小嘈杂的 1 分钟 K 线优雅平滑为 5 分钟标准切片段。
- **阶段**: `1m .csv -> 5m .csv`

### 3. [3-KLine-Slicer](https://github.com/Ziqi/3-KLine-Slicer)
- **职能**: 模型喂养压榨机。
- **机制**: 对 K 线数据进行批量的健康体检，清理断点，并将选定的股票组融合、压铸成符合 Kronos 规范的时序特征字典大包 (`.pkl`)。
- **阶段**: `5m .csv -> .pkl Dataset`

### 4. [4-Kronos-Trainer-GUI](https://github.com/Ziqi/4-Kronos-Trainer-GUI)
- **职能**: 脑机训练器 (引擎控制台)。
- **机制**: 图形化封装了 PyTorch 训练链路（包含 Tokenizer 与 Predictor 两阶段）。配置了早期停止 (Early Stopping)、余弦退火 (Cosine Annealing) 等高级特性，利用本地隔离虚拟环境进行深度炼丹。
- **阶段**: `.pkl Dataset -> Finetuned Models`

### 5. [5-Kronos-Predictor-GUI](https://github.com/Ziqi/5-Kronos-Predictor-GUI)
- **职能**: 核心脑机推演终端 (Inference Demo)。
- **机制**: 挂载微调好的 Tokenizer 和 Predictor 脑区，读取最新的 5 分钟真实数据，执行特征缩放 (Transform) 与自回归推演，最后降维解算 (Inverse) 吐出未来包含真实价格的预测游走路线。
- **阶段**: `5m .csv + Models -> Future .csv`

---

## 🔧 克隆与组装指南 (Clone Instructions)

因为本仓库是一个“组装体 (Umbrella Repo)”，克隆时必须携带子模块更新参数：

```bash
git clone --recursive https://github.com/Ziqi/KLine-Kronos-Suite.git
```
或者在克隆后初始化它们：
```bash
git submodule init
git submodule update
```

## 🌌 为什么这样设计？
将三者独立解耦的初衷在于**流水线复用与风险隔离**。抓取层、计算层和张量层应该有各自的演进周期。任何一个模块的崩溃，都不会影响到已沉淀下来的物理数据缓存块。所有组件通过统一的 `KLine-Kronos-Suite` 进行聚合管理。

## Acknowledgements (特别鸣谢)
本数据处理矩阵由衷感谢并致敬 **Kronos** 的开源贡献！
本项目作为数据采集与预处理的重要一环，旨在为训练或微调优秀的金融时序预测预训练模型提供弹药。如果您想深入了解本项目所致敬并支持的 **Kronos** 大模型底座，敬请关注原作者项目： [@shiyu-coder/Kronos](https://github.com/shiyu-coder/Kronos).

---
`Design Language: Cyber-Gold` | `Architecture: Micro-Station Git Submodules`
