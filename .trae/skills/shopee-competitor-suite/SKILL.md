---
name: shopee-competitor-suite
description: "东南亚电商竞品情报套件：采集Shopee 6国竞品数据，生成分析报告。Invoke when user asks to monitor Shopee competitors, collect Southeast Asia competitor data, or generate competitor analysis reports."
---

# Shopee竞品情报套件

> 一键采集东南亚6国竞品数据，自动生成分析报告

## 功能概述

| 功能 | 说明 |
|------|------|
| 数据采集 | 从知虾平台采集 Shopee 6国市场数据 |
| 批次导出 | 自动分批导出超过100条的数据 |
| 断点续传 | 支持进度保存，中断后可继续 |
| 数据分析 | 计算市场份额、价格分布 |
| 报告生成 | 生成 CSV/JSON/HTML 报告 |

## 支持的市场

| 代码 | 国家/地区 | 货币 |
|------|-----------|------|
| MY | 马来西亚 | MYR |
| ID | 印尼 | IDR |
| TH | 泰国 | THB |
| PH | 菲律宾 | PHP |
| SG | 新加坡 | SGD |
| VN | 越南 | VND |
| TW | 中国台湾 | TWD |
| BR | 巴西 | BRL |
| MX | 墨西哥 | MXN |

## 预置产品线

| 代码 | 名称 | 关键词示例 |
|------|------|-----------|
| OP | 手机云台/稳定器 | insta360 flow, hohem, zhiyun |
| OM | 手机支架/智能跟随 | insta360 flow 2 |
| MIC_400_1000 | 麦克风 400-1000价位 | hollyland mic |
| MIC_1000PLUS | 麦克风 1000+价位 | insta360 mic pro |

## 使用方法

### CDP 模式（推荐）

复用 Chrome 浏览器登录状态：

```powershell
# 进入脚本目录
cd .trae/skills/shopee-scraper/scripts

# 检查 CDP Proxy 状态
python run_daily.py check

# 自定义采集
python run_daily.py cdp --sites MY ID --keyword insta360

# 完整采集
python run_daily.py cdp
```

### 前置条件

1. Chrome 浏览器已开启远程调试
2. 已在 Chrome 中登录知虾网站 (shopee.menglar.com)
3. CDP Proxy 已启动 (localhost:3456)

## 工作流

```
用户指令 → 解析参数 → 数据采集 → 生成报告
    │           │           │           │
    ▼           ▼           ▼           ▼
"采集马来西亚  → 站点:MY    → shopee-scraper → CSV文件
 OP产品线"     关键词      → 批次导出      → 分析JSON
```

## 示例用法

### 完整流程

```
请帮我运行Shopee竞品监控：
1. 采集马来西亚站点的insta360产品数据
2. 分析数据并生成报告
```

### 仅采集

```
采集Shopee马来西亚站点的insta360产品数据，下载全部数据（不止100条）
```

### 自定义关键词

```
采集马来西亚站点的 hohem isteady 产品数据
```

## 安全边界

- **不会存储账号密码**：只保存会话 cookies
- **不会修改现有文件**：只生成新文件
- **遇到验证码会暂停**：等待用户手动处理
- **敏感文件已排除**：cookies.json、*.env、secrets.yaml 不推送 GitHub

## 文件结构

```
.trae/skills/
├── shopee-competitor-suite/    # 主 Skill
│   └── SKILL.md
├── shopee-scraper/             # 数据采集子 Skill
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── run_daily.py        # 统一入口
│   │   ├── zhixia_cdp_scraper.py  # CDP采集器
│   │   └── zhixia_scraper.py   # Playwright采集器
│   ├── config/
│   │   └── competitors.yaml    # 配置文件
│   └── data/
│       └ downloads/            # 下载目录
│       └ cookies.json          # 会话状态（不推送）
```

## 配置文件

配置文件位于 `.trae/skills/shopee-scraper/config/competitors.yaml`：

```yaml
sites:
  - code: MY
    name: 马来西亚
    currency: MYR

product_lines:
  OP:
    name: "手机云台"
    keywords:
      - "insta360 flow"
      - "hohem isteady"
      - "zhiyun smooth"
```

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| CDP Proxy 未就绪 | 检查 Chrome 远程调试是否开启 |
| 登录失败 | 在 Chrome 中手动登录知虾网站 |
| 导出失败 | 检查页面选择器是否更新 |
| 数据为空 | 确认关键词有搜索结果 |
| 网络连接失败 | 使用 SSH 方式推送 git |

## 版本历史

- v3.2 (2026-06) - 批次导出、断点续传、下载监控、Trae/OpenCode 格式
- v3.1 (2025-06) - CDP 模式，复用 Chrome 登录状态
- v3.0 (2025-06) - 重构采集流程