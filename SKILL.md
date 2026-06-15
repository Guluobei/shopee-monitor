---
name: shopee-competitor-suite
description: 东南亚电商竞品情报套件：一键采集6国市场数据，自动生成竞品分析报告并推送飞书
triggers:
  - "帮我监控Shopee竞品"
  - "采集东南亚竞品数据"
  - "生成竞品分析报告"
  - "监控OP产品线在马来西亚的价格"
  - "对比6国市场的云台产品销量"
  - "运行Shopee竞品监控"
  - "采集Shopee数据并分析"
  - "东南亚电商竞品情报"
dependencies:
  skills:
    - shopee-scraper
    - competitor-analysis
    - report-generator
---

# Shopee竞品情报套件

> 一句话钩子：**一键采集东南亚6国竞品数据，自动生成分析报告，省去每天手动查价的痛苦**

## 你什么时候需要它？

1. **日常竞品监控**：每天需要追踪竞品价格变化，手动查太耗时
2. **新品定价决策**：准备在东南亚市场发布新品，需要了解同类产品价格区间
3. **市场趋势分析**：想了解某个品类在不同国家的销量分布和竞争格局

## 它会交付什么？

- **CSV数据报告**：包含商品名称、价格、销量、店铺、评分等完整字段
- **分析摘要JSON**：按站点、产品线统计的市场份额、价格分布
- **HTML可视化报告**（可选）：含图表的竞品分析报告
- **飞书卡片推送**（可选）：直接发送到飞书群聊

## 快速开始

### TRAE用户安装

```powershell
# 安装完整套件
Copy-Item -Path "shopee-competitor-suite" -Destination "$env:USERPROFILE\.trae\skills\" -Recurse

# 或仅安装单个子Skill
Copy-Item -Path "shopee-competitor-suite\skills\shopee-scraper" -Destination "$env:USERPROFILE\.trae\skills\shopee-scraper" -Recurse
```

### 依赖安装

```powershell
pip install playwright pandas pyyaml openpyxl
playwright install chromium
```

## 工作流

```
用户指令 → 解析参数 → 调用子Skill → 生成报告
    │           │           │           │
    │           │           │           │
    ▼           ▼           ▼           ▼
"采集马来西亚  → 站点:MY    → shopee-scraper → CSV文件
 OP产品线"     产品线:OP   → competitor-analysis → 分析JSON
                          → report-generator → HTML报告/飞书卡片
```

## 子Skill说明

| 子Skill | 职责 | 可独立使用 |
|---------|------|:----------:|
| `shopee-scraper` | 从知虾平台采集Shopee 6国数据 | ✓ |
| `competitor-analysis` | 分析数据，计算市场份额、价格分布 | ✓ |
| `report-generator` | 生成HTML报告，推送飞书 | ✓ |

## 示例用法

### 完整流程

```
请帮我运行Shopee竞品监控：
1. 采集马来西亚和印尼站点的OP产品线数据
2. 分析数据并生成报告
3. 将报告发送到飞书
```

### 仅采集

```
采集Shopee马来西亚站点的云台产品数据
```

### 仅分析

```
分析已有的竞品数据，计算市场份额
```

## 安全边界

- **不会修改或删除**任何现有文件，只生成新文件
- **不会泄露**知虾账号密码或API密钥
- **遇到验证码时会暂停**，等待用户手动处理
- **数据量过大时会提示**，避免一次性导出过多数据

## 文件结构

```
shopee-competitor-suite/
├── SKILL.md                    # 本文件（主入口）
├── README.md                   # 套件说明
├── config/
│   └── competitors.yaml        # 共享配置
├── references/
│   ├── market-insights.md      # 市场洞察
│   ├── product-lines.md        # 产品线定义
│   └ competitor-metrics.md     # 指标定义
├── tools/
│   └ check-suite.ps1           # 套件检查
├── assets/
│   └ workflow-diagram.png      # 工作流图
├── examples/
│   └ test-prompts.json         # 测试prompt
│   └ sample-data/              # 样例数据
├── skills/
│   ├── shopee-scraper/         # 子Skill 1
│   ├── competitor-analysis/    # 子Skill 2
│   └ report-generator/         # 子Skill 3
```

## 支持的市场

| 代码 | 国家 | Shopee域名 |
|------|------|------------|
| MY | 马来西亚 | shopee.com.my |
| ID | 印度尼西亚 | shopee.co.id |
| TH | 泰国 | shopee.co.th |
| PH | 菲律宾 | shopee.ph |
| SG | 新加坡 | shopee.sg |
| VN | 越南 | shopee.vn |

## 预置产品线

| 代码 | 名称 | 关键词示例 |
|------|------|-----------|
| OP | 手机云台/稳定器 | insta360 luna ultra |
| OM | 手机支架/智能跟随 | insta360 flow 2, hohem, zhiyun |
| MIC_400_1000 | 麦克风 400-1000价位 | hollyland mic |
| MIC_1000PLUS | 麦克风 1000+价位 | insta360 mic pro, rode |

## 注意事项

1. **登录状态**：首次使用需要在浏览器中扫码登录知虾
2. **账号要求**：需要有知虾账号（shopee.menglar.com）
3. **采集间隔**：建议设置合理间隔，避免触发反爬
4. **数据量**：根据账号等级，单次导出可能有数量限制

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| 登录失败 | 检查cookies是否过期，手动登录后重试 |
| 导出按钮找不到 | 页面结构可能更新，需更新选择器 |
| 数据为空 | 确认关键词在目标市场有搜索结果 |
| 验证码弹窗 | 脚本会尝试关闭，如失败需手动处理 |