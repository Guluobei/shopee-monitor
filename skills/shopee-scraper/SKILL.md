---
name: shopee-scraper
description: Shopee竞品数据采集：从知虾平台采集东南亚竞品价格和销量数据，支持传统模式和优化模式
triggers:
  - "采集Shopee数据"
  - "抓取马来西亚云台产品"
  - "导出OP产品线数据"
  - "运行知虾采集"
  - "采集东南亚竞品"
  - "快速采集竞品"
  - "优化版采集"
standalone: true
---

# Shopee竞品数据采集

> 从知虾平台自动化采集东南亚Shopee竞品数据，支持**传统模式**和**优化模式**

## 🚀 两种模式对比

| 特性 | 传统模式 | 优化模式 |
|------|----------|----------|
| **Cookie管理** | 每次检测 | 30分钟缓存 |
| **登录速度** | 较慢 | 快速跳过 |
| **选择器** | 固定，易失效 | 自适应+缓存 |
| **等待时间** | 固定 | 智能调整 |
| **失败处理** | 直接报错 | 多级重试 |
| **断点续传** | 无 | 有 |
| **页面改版** | 易失败 | 自动降级 |

## ⚡ 优化模式（推荐）

优化模式在**流畅度**和**可靠性**上有大幅提升：

### 核心优势
- **30分钟Cookie缓存**：30分钟内不重复登录
- **快速验证**：10秒检测Cookie有效性
- **Session复用**：同一进程内不重复启动浏览器
- **自适应选择器**：页面改版自动降级
- **选择器缓存**：记住成功的，第二次直接用
- **智能等待**：根据历史自动调整等待时间
- **多级重试**：偶发错误自动恢复
- **断点续传**：中断后可继续

### 使用方法

```powershell
# 登录检查
python scripts/zhixia_monitor.py login

# 采集数据
python scripts/zhixia_monitor.py collect --sites MY ID

# 完整流程
python scripts/zhixia_monitor.py run --sites MY --product-lines OP

# 清除缓存（如页面改版）
python scripts/zhixia_monitor.py cache

# 查看状态
python scripts/zhixia_monitor.py status
```

### Python API

```python
from scripts.optimized_scraper import OptimizedZhixiaScraper

# 创建采集器
scraper = OptimizedZhixiaScraper(config_path='config/competitors.yaml')

# 初始化（登录）
success, reason = scraper.initialize()
if not success:
    print(f"登录失败: {reason}")
    exit(1)

# 批量采集（支持断点续传）
results = scraper.scrape_multiple(
    sites=['MY', 'ID'],
    keywords=['insta360', '手机云台'],
    resume=True
)

print(f"成功: {results['completed']}, 失败: {results['failed']}")

# 关闭
scraper.close()
```

## 📦 传统模式

传统模式经过多年验证，稳定可靠：

```powershell
# CDP 模式（推荐）
python run_daily.py cdp --sites MY ID --product-lines OP OM

# Playwright 模式
python run_daily.py pw --sites MY
```

详细说明请参考下方文档。

## 📁 文件结构

```
skills/shopee-scraper/
├── SKILL.md                        # 本文件
├── README.md                       # 详细说明
├── config/
│   └── competitors.yaml            # 配置文件
├── scripts/
│   ├── __init__.py               # 优化版模块入口
│   ├── zhixia_monitor.py         # 优化版主程序
│   ├── optimized_scraper.py       # 优化版采集器
│   ├── optimized_login_manager.py # 优化版登录管理
│   ├── optimized_cookie_manager.py # Cookie管理
│   ├── adaptive_selector.py       # 自适应选择器
│   ├── smart_wait.py             # 智能等待
│   ├── data_processor.py         # 数据处理
│   ├── run_daily.py             # 传统模式入口
│   ├── zhixia_cdp_scraper.py   # CDP采集器
│   ├── zhixia_scraper.py        # Playwright采集器
│   └── zhixia_login.py          # 登录管理
└── data/
    ├── downloads/                # 下载文件
    ├── cookies.json             # Cookie
    ├── cache/                   # 缓存目录
    └── screenshots/             # 截图
```

## 🔧 模块说明

### 优化版模块

| 模块 | 功能 |
|------|------|
| `optimized_cookie_manager.py` | Cookie新鲜度检测、快速验证 |
| `optimized_login_manager.py` | 优化版登录管理 |
| `adaptive_selector.py` | 自适应选择器 |
| `smart_wait.py` | 智能等待 |
| `optimized_scraper.py` | 优化版采集器 |

### 传统模块

| 模块 | 功能 |
|------|------|
| `zhixia_login.py` | 登录管理 |
| `zhixia_scraper.py` | Playwright采集器 |
| `zhixia_cdp_scraper.py` | CDP采集器 |

## 📊 支持的市场

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

## ⚙️ 配置说明

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
```

## 💾 缓存文件

优化版会生成以下缓存文件：

- `.cache/selector_cache_*.json` - 选择器缓存
- `.cache/wait_history.json` - 等待历史
- `.cache/checkpoint_*.json` - 断点记录
- `.cookie_validation_cache.json` - Cookie验证缓存

如遇页面改版导致失败，可运行 `cache` 命令清除缓存。

## ❓ 如何选择

| 场景 | 推荐模式 |
|------|----------|
| 日常监控（定期运行） | 优化模式 |
| 页面经常改版的网站 | 优化模式 |
| 追求稳定性 | 传统模式 |
| 首次使用 | 优化模式 |
| 大批量采集 | 优化模式 |

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| 登录失败 | 删除 `data/cookies.json` 后重新登录 |
| 选择器失效（优化模式） | 运行 `cache` 命令清除选择器缓存 |
| 采集失败 | 检查网络连接，确保知虾账号有效 |
| 下载失败 | 检查下载目录权限 |
| CDP未就绪 | 检查 Chrome 远程调试是否开启 |

## 📖 详细文档

- [详细使用说明](./README.md)
- [定时任务配置](./cron_config.md)

## 版本历史

- **v4.0 (2026-06)** - 新增优化模式，大幅提升流畅度和可靠性
  - 30分钟Cookie缓存
  - 自适应选择器 + 选择器缓存
  - 智能等待 + 多级重试
  - 断点续传
- v3.2 (2026-06) - 批次导出、断点续传、下载监控、输入优化
- v3.1 (2025-06) - 添加 CDP 模式
- v3.0 (2025-06) - 重构采集流程
- v2.0 (2024-01) - 添加数据处理
- v1.0 (2024-01) - 初始版本
