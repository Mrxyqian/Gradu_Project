# Paper Ablation Summary

| Index | Group | Experiment | Runs | AUC | F1 | Recall | Precision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | shared_baseline | 01_shared_baseline_baseline_original | 3 | 0.970977 +- 0.001569 | 0.803801 +- 0.003908 | 0.855906 +- 0.003339 | 0.757693 +- 0.006093 |
| 2 | components | 02_components_no_residual | 3 | 0.970589 +- 0.001772 | 0.803732 +- 0.005884 | 0.866768 +- 0.009611 | 0.749258 +- 0.003662 |
| 3 | components | 03_components_no_norm | 3 | 0.971169 +- 0.001243 | 0.804858 +- 0.004457 | 0.851833 +- 0.012759 | 0.763008 +- 0.012891 |
| 4 | components | 04_components_relu_activation | 3 | 0.970668 +- 0.001472 | 0.802128 +- 0.004416 | 0.854548 +- 0.025486 | 0.756267 +- 0.012232 |
| 5 | components | 05_components_linear_head | 3 | 0.970847 +- 0.001772 | 0.804642 +- 0.005082 | 0.860489 +- 0.021172 | 0.755904 +- 0.008914 |
