# A/B实验：CUPED 提升 ARPU 指标敏感度

这个仓库提供一个可直接运行的脚本：`cuped_arpu_opt.py`，用于在 A/B 实验中对 ARPU 做 CUPED（Controlled-Experiment Using Pre-Experiment Data）降方差，从而提升检验敏感度。

## 思路

- 原始估计：
  - `effect_raw = mean(ARPU_treat) - mean(ARPU_control)`
- CUPED 调整：
  - `ARPU_cuped = ARPU_post - (X_pre - mean(X_pre)) @ theta`
  - 其中 `theta = (X'X)^(-1)X'Y`
- 目标：
  - 在**不改变无偏性的前提下**降低方差，提升 t 统计量与检验功效。

## 输入数据格式（CSV）

最少包含以下列：

- `user_id`: 用户唯一ID（每行一个用户）
- `group`: 分组（`control/treatment` 或 `0/1`）
- `arpu`: 实验期 ARPU
- 一个或多个实验前协变量（例如 `arpu_pre_7d`, `arpu_pre_14d`）

## 运行方式

```bash
python cuped_arpu_opt.py \
  --input your_data.csv \
  --user-col user_id \
  --group-col group \
  --outcome-col arpu \
  --pre-cols arpu_pre_7d arpu_pre_14d
```

## 输出解释

- `Raw effect / Raw SE / Raw t-stat`: 原始实验结果
- `CUPED effect / CUPED SE / CUPED t-stat`: CUPED 后结果
- `Variance reduction`: 方差下降比例
- `Sensitivity gain`: `Raw SE / CUPED SE`，越大越好

## 实践建议（ARPU 场景）

1. 优先选与实验期 ARPU 高相关、且实验不会影响的前置特征。  
2. 统一 winsorize/截尾 规则，先处理极端值再拟合 CUPED。  
3. 避免引入泄漏变量（实验期间才可观测到的特征）。  
4. 按用户粒度聚合后再运行，避免重复曝光造成方差估计偏差。
