# 4-Kronos-Trainer-GUI 🧠⚙️

**KLine Kronos Suite - 脑机训练器 (Program 4)**

这是一个独立的图形化控制中枢，专门用于指挥底层 PyTorch 引擎进行 Kronos 模型的两阶段训练（Tokenizer & Predictor）。它被设计为运行在一个纯净、隔离的 Python 虚拟环境 (venv) 中，确保算力资源的绝对安全与依赖隔离。

## 🌟 核心特性 (Key Features)

- **流式接管**: 即时捕获底层 Python 训练脚本的标准输出，在图形界面的黑色流式看板中打印 Loss 和 Epoch 进度。
- **独立生命周期管理**: 可以一键安全阻断 (Kill) 失控的训练进程。
- **工业级参数集成**: 底层嵌入了 30 Epochs、Cosine Annealing Scheduler（余弦退火学习率）、及其附带 Patience = 5 的 Early Stopping (早停) 机制，防止模型在本地炼丹时过拟合。
- **直通底层查验**: 训练完成后，支持一键打开专属的 `models/` 产出目录。

## 🛠 运行逻辑

1. 挂载由 `3-KLine-Slicer` 生产出的庞大 `.pkl` 切片字典。
2. 优先执行 **1. Tokenizer 模式**，教会神经网络如何把行情“压缩”成特定的单词。
3. 执行 **2. Predictor 模式**，让主 Transformer 大脑吞食这些单词，并学会在 90 回望下预测未来的走势。此时产出专属微调模型。

---
`Design Language: Cyber-Gold (Flat Dark Gold)`
