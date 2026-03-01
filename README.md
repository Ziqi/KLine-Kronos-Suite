# KLine Kronos Suite 💻📈

**KLine Kronos Suite** 是一套端到端、全链路的 A 股（及全市场）高频金融时序数据处理与特征提纯矩阵。专为 **Kronos (Chronos by Amazon)** 等大语言/序列模型量身打造的“数据源泉”。本套件将原始的分钟级金融数据，完美转化为适用于 Kronos 时序预测模型的标准格式。

整个 Suite 包含三大核心微型基站，遵循严格的 **"Flat Dark Gold (极客暗金)"** 设计美学和极客交互理念：

## 🚀 The Trifecta (核心三剑客)

本项目采用子模块 (Git Submodules) 的形式聚合。点击下方各个独立工程查看具体源码与说明：

### 1. [KLine-Matrix-Station (1-KLine-Extract)](https://github.com/Ziqi/KLine-Matrix-Station)
- **职能**: 最前线的物理爬虫雷达。
- **机制**: 用内置的军工级防封杀引擎和剪贴板自动嗅探，并发拉取全市场 1 分钟颗粒度 K 线。
- **阶段**: `Text -> 1m .csv`

### 2. [KLine-Resample-Studio (2-KLine-Resample)](https://github.com/Ziqi/KLine-Resample-Studio)
- **职能**: 降噪与重组基座。
- **机制**: 严格遵循 A 股时间线属性（`closed='right', label='right'`），将细小嘈杂的 1 分钟 K 线优雅平滑为 5 分钟标准切片段。
- **阶段**: `1m .csv -> 5m .csv`

### 3. [KLine-Slicer (3-KLine-Slicer)](https://github.com/Ziqi/KLine-Slicer)
- **职能**: 模型喂养压榨机。
- **机制**: 对接预训练专家的 `scaler_*.pkl` 均值/方差加密归一化文件，对数据进行批量的健康体检、清洗缺口，最后切割压铸成多维度的 `.npy` 张量。
- **阶段**: `5m .csv + Scalers -> .npy Tensors`

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
本数据处理矩阵由衷感谢并致敬 **Chronos (by Amazon Science)** 团队的开源贡献！
如果想深入了解支撑和启发本项目背后的时间序列预测模型，敬请关注官方开源项目： [@amazon-science/chronos-forecasting](https://github.com/amazon-science/chronos-forecasting).

---
`Design Language: Cyber-Gold` | `Architecture: Micro-Station Git Submodules`
