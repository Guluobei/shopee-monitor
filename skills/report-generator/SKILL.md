---
name: report-generator
description: 竞品报告生成：将分析结果转换为可视化HTML报告并推送飞书
triggers:
  - "生成竞品报告"
  - "发送报告到飞书"
  - "导出HTML报告"
  - "创建飞书卡片"
  - "生成分析报告"
standalone: true
---

# 竞品报告生成

> 将分析结果转换为可视化HTML报告，支持飞书推送

## 功能

- **HTML报告**：含图表的可视化报告
- **飞书卡片**：发送到飞书群聊
- **CSV导出**：标准数据格式
- **摘要生成**：关键指标汇总

## 使用方法

### Agent调用

```
生成竞品分析报告并发送到飞书
```

```
将分析结果导出为HTML报告
```

### 命令行

```powershell
# 生成HTML报告
python scripts/report_builder.py --input summary.json --output report.html

# 发送飞书
python scripts/feishu_sender.py --card feishu_card.json --webhook <webhook_url>
```

## 输入

- **分析摘要JSON**：`competitor-analysis` 输出的摘要文件
- **CSV数据**：可选，用于详细报告

## 输出

| 输出 | 格式 | 说明 |
|------|------|------|
| HTML报告 | `.html` | 可视化报告，含图表 |
| 飞书卡片 | - | 发送到飞书群聊 |
| PDF报告 | `.pdf` | 可选，适合打印 |

## 报告内容

1. **数据概况**：总记录数、涉及站点、产品线
2. **站点对比**：各站点商品数、销量、均价对比
3. **产品线分析**：各产品线竞争格局
4. **热销榜单**：Top10热销商品
5. **价格分布**：价格区间分布图

## 飞书集成

### 配置Webhook

```yaml
feishu:
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
  # 或使用飞书App ID/Secret
  app_id: "cli_xxx"
  app_secret: "xxx"
```

### 卡片模板

```json
{
  "card": {
    "header": {
      "title": "Shopee竞品监控报告"
    },
    "elements": [
      {
        "tag": "div",
        "text": "今日采集数据：XXX条"
      }
    ]
  }
}
```

## 安全边界

- **不会泄露**Webhook URL或App Secret
- **报告不含敏感信息**（账号、密码）

## 文件结构

```
report-generator/
├── SKILL.md
├── scripts/
│   ├── report_builder.py
│   └ feishu_sender.py
├── templates/
│   ├── report_template.html
│   └ feishu_card.json
├── output/
│   └ reports/
```