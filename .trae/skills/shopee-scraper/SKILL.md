---
name: shopee-scraper
description: "Shopee竞品数据采集：从知虾平台采集东南亚竞品价格和销量数据，支持批次导出和断点续传。Invoke when user asks to collect Shopee competitor data, scrape Southeast Asia product prices, or export competitor analysis data."
---

# Shopee竞品数据采集

> 从知虾平台自动化采集东南亚Shopee竞品数据

## 功能特性

| 功能 | 说明 |
|------|------|
| 多站点支持 | 马来西亚、印尼、泰国、菲律宾、新加坡、越南、台湾、巴西、墨西哥 |
| 批次导出 | 自动分批导出超过100条的数据（知虾平台限制每批100条） |
| 断点续传 | 支持进度保存，中断后可继续未完成的批次 |
| 下载监控 | 自动等待下载完成并检测新文件 |
| 输入优化 | 使用 JS 设置值并触发 input 事件，避免值累积问题 |
| CDP 模式 | 复用 Chrome 浏览器登录状态，无需独立浏览器 |

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

## 使用方法

### CDP 模式（推荐）

复用 Chrome 浏览器登录状态：

```powershell
# 进入脚本目录
cd scripts

# 检查 CDP Proxy 状态
python run_daily.py check

# 测试模式（单站点单关键词）
python run_daily.py test

# 自定义采集
python run_daily.py cdp --sites MY ID --keyword insta360

# 完整采集（所有站点所有产品线）
python run_daily.py cdp
```

### 前置条件

1. Chrome 浏览器已开启远程调试（`chrome://inspect/#remote-debugging`）
2. 已在 Chrome 中登录知虾网站
3. CDP Proxy 已启动（运行 `check` 命令检查）

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--sites` | 站点代码列表，如 `MY ID TH` |
| `--keyword` | 直接搜索指定关键词 |
| `--product-lines` | 产品线代码列表 |

## 配置说明

配置文件位于 `config/competitors.yaml`：

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
      - "insta360 flow 2"
      - "hohem isteady"
      - "zhiyun smooth"
```

## 文件结构

```
shopee-scraper/
├── SKILL.md               # Skill文档
├── config/
│   └── competitors.yaml   # 配置文件
├── scripts/
│   ├── run_daily.py       # 统一入口
│   ├── zhixia_cdp_scraper.py  # CDP采集器（推荐）
│   ├── zhixia_scraper.py  # Playwright采集器
│   └── zhixia_login.py    # 登录管理
└── data/
    ├── downloads/         # 下载的Excel
    └ cookies.json         # 登录状态（不推送）
```

## 输出格式

导出的 Excel 文件包含以下字段：

| 列名 | 说明 |
|------|------|
| 商品名称 | 商品标题 |
| 店铺名称 | 店铺名称 |
| 价格 | 当前售价 |
| 销量 | 累计销量 |
| 评分 | 商品评分 |
| 商品链接 | 详情页URL |

## 依赖安装

```bash
pip install playwright pandas pyyaml openpyxl requests
playwright install chromium  # 仅 Playwright 模式需要
```

## CDP 模式设置

1. 打开 Chrome 浏览器
2. 访问 `chrome://inspect/#remote-debugging`
3. 勾选 **Allow remote debugging for this browser instance**
4. 登录知虾网站 `https://shopee.menglar.com`
5. 运行 `python run_daily.py check` 确认连接

## 安全说明

- **不会存储账号密码**：只保存会话 cookies
- **敏感文件已排除**：cookies.json 不推送 GitHub
- **遇到验证码会暂停**：等待用户手动处理

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| CDP Proxy 未就绪 | 检查 Chrome 远程调试是否开启 |
| 登录失败 | 在 Chrome 中手动登录知虾网站 |
| 导出失败 | 检查页面选择器是否更新 |
| 数据为空 | 确认关键词有搜索结果 |
| 下载失败 | 检查下载目录权限 |

## 版本历史

- v3.2 (2026-06) - 批次导出、断点续传、下载监控、输入优化
- v3.1 (2025-06) - 添加 CDP 模式，复用 Chrome 登录状态
- v3.0 (2025-06) - 重构采集流程，优化登录管理