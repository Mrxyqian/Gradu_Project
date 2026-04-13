# 论文对比实验结果

| 序号 | 实验分组 | 主干结构 | 隐藏层 | 优化器 | AUC-ROC | F1 | Recall | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | network_structure | backbone_A_shallow | 128-256-128 | adamw | 0.968151 | 0.80062 | 0.789206 | success |
| 2 | network_structure | backbone_B_medium | 256-256-256 | adamw | 0.968619 | 0.8 | 0.798371 | success |
| 3 | network_structure | backbone_C_deep | 256-512-512-256-256 | adamw | 0.96839 | 0.800817 | 0.798371 | success |
| 6 | optimizer | backbone_C_deep | 256-512-512-256-256 | adamw | 0.96839 | 0.800817 | 0.798371 | success |
| 7 | optimizer | backbone_C_deep | 256-512-512-256-256 | adam | 0.968528 | 0.799691 | 0.790733 | success |
| 8 | optimizer | backbone_C_deep | 256-512-512-256-256 | sgd | 0.956539 | 0.761975 | 0.785642 | success |
