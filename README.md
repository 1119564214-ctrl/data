# A/B实验：CUPED 提升 ARPU 与人均下载(avg_down)指标敏感度

这个仓库提供可直接运行脚本：`cuped_arpu_opt.py`，用于在 A/B 实验中对 ARPU 做 CUPED（Controlled-Experiment Using Pre-Experiment Data）降方差，并可在同一次运行中新增 `avg_down`（人均下载）指标的敏感性提升检验。

## 思路

- 原始估计：
  - `effect_raw = mean(metric_treat) - mean(metric_control)`
- CUPED 调整：
  - `metric_cuped = metric_post - (X_pre - mean(X_pre)) @ theta`
  - 其中 `theta = (X'X)^(-1)X'Y`
- 目标：
  - 在**不改变无偏性的前提下**降低方差，提升 t 统计量与检验功效。

## 输入数据格式（CSV）

最少包含以下列：

- `user_id`: 用户唯一ID（每行一个用户）
- `group`: 分组（`control/treatment` 或 `0/1`）
- `arpu`: 实验期 ARPU
- `avg_down`（可选）: 实验期人均下载
- 每个指标对应一个或多个实验前协变量（例如 `arpu_pre_7d`, `avg_down_pre_7d`）

## 运行方式

### 仅跑 ARPU

```bash
python cuped_arpu_opt.py \
  --input your_data.csv \
  --user-col user_id \
  --group-col group \
  --outcome-col arpu \
  --pre-cols arpu_pre_7d arpu_pre_14d
```

### ARPU + avg_down 同时跑

```bash
python cuped_arpu_opt.py \
  --input your_data.csv \
  --user-col user_id \
  --group-col group \
  --outcome-col arpu \
  --pre-cols arpu_pre_7d arpu_pre_14d \
  --avg-down-col avg_down \
  --avg-down-pre-cols avg_down_pre_7d avg_down_pre_14d
```

## 输出解释

每个指标都会输出一段报告：

- `Raw effect / Raw SE / Raw t-stat`: 原始实验结果
- `CUPED effect / CUPED SE / CUPED t-stat`: CUPED 后结果
- `Variance reduction`: 方差下降比例
- `Sensitivity gain`: `Raw SE / CUPED SE`，越大越好

## 实践建议（ARPU + avg_down）

1. 每个指标使用其自身高相关的前置特征，不建议混用不相关协变量。  
2. 统一 winsorize/截尾 规则，先处理极端值再拟合 CUPED。  
3. 避免引入泄漏变量（实验期间才可观测到的特征）。  
4. 按用户粒度聚合后再运行，避免重复曝光造成方差估计偏差。
