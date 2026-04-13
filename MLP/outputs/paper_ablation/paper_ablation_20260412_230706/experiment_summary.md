# Paper Ablation Summary

| Index | Group | Experiment | Runs | AUC | F1 | Recall | Precision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | shared_baseline | 01_shared_baseline_baseline_original | 1 | 0.969177 +- 0.0 | 0.8035 +- 0.0 | 0.818228 +- 0.0 | 0.789293 +- 0.0 |
| 2 | components | 02_components_no_residual | 1 | 0.969639 +- 0.0 | 0.805263 +- 0.0 | 0.856925 +- 0.0 | 0.759477 +- 0.0 |
| 3 | components | 03_components_no_norm | 1 | 0.968894 +- 0.0 | 0.79775 +- 0.0 | 0.830448 +- 0.0 | 0.767529 +- 0.0 |
| 4 | components | 04_components_relu_activation | 1 | 0.9695 +- 0.0 | 0.799614 +- 0.0 | 0.844196 +- 0.0 | 0.759505 +- 0.0 |
| 5 | components | 05_components_linear_head | 1 | 0.968163 +- 0.0 | 0.798046 +- 0.0 | 0.831976 +- 0.0 | 0.766776 +- 0.0 |
