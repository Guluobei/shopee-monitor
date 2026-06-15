---
name: shopee-scraper
description: Shopee竞品数据采集：从知虾平台采集东南亚竞品价格和销量数据
triggers:
  - "采集Shopee数据"
  - "抓取马来西亚云台产品"
  - "导出OP产品线数据"
  - "运行知虾采集"
  - "采集东南亚竞品"
standalone: true
---

# Shopee竞品数据采集

> 从知虾平台自动化采集东南亚Shopee竞品数据

## 功能特性

- **多站点支持**：马来西亚、印尼、泰国、菲律宾、新加坡、越南、台湾、巴西、墨西哥
- **多产品线**：OP（云台）、OM（支架）、MIC（麦克风）等
- **两种采集模式**：
  - **CDP 模式**：复用 Chrome 浏览器登录状态，无需独立浏览器
  - **Playwright 模式**：独立启动浏览器，支持无头模式
- **自动导出**：点击导出按钮下载Excel文件
- **数据处理**：自动解析、合并、去重数据

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

复用 Chrome 浏览器登录状态，无需独立启动浏览器：

```powershell
# 检查 CDP Proxy 状态
python run_daily.py check

# 测试模式（单站点单关键词）
python run_daily.py test

# 自定义采集
python run_daily.py cdp --sites MY ID --product-lines OP OM

# 完整采集（所有站点所有产品线）
python run_daily.py cdp
```

**前置条件**：
1. Chrome 浏览器已开启远程调试（`chrome://inspect/#remote-debugging`）
2. 已在 Chrome 中登录知虾网站
3. CDP Proxy 已启动（运行 `check` 命令检查）

### Playwright 模式

独立启动浏览器，适合首次登录或无头模式：

```powershell
# 可见模式（便于登录）
python run_daily.py pw --sites MY

# 无头模式（后台运行）
python run_daily.py pw --sites MY --headless
```

### Agent调用

```
使用 CDP 模式采集Shopee马来西亚站点的云台产品数据
```

```
采集马来西亚和印尼的OP、OM产品线数据
```

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
shopee-competitor-suite/
├── config/
│   └── competitors.yaml        # 配置文件
├── skills/shopee-scraper/
│   ├── SKILL.md               # Skill文档
│   └── scripts/
│       ├── run_daily.py       # 统一入口
│       ├── zhixia_cdp_scraper.py  # CDP采集器（推荐）
│       ├── zhixia_scraper.py  # Playwright采集器
│       ├── zhixia_login.py    # 登录管理
│       └── data_processor.py  # 数据处理
│   ├── data/
│   │   ├── downloads/         # 下载的Excel
│   │   ├── cookies.json       # 登录状态
│   │   └── screenshots/       # 截图
│   └── output/
│       ├── *.csv              # 输出CSV
│       └── consolidated/      # 合并数据
```

## 输出格式

| 列名 | 说明 |
|------|------|
| 采集日期 | 数据采集日期 |
| 采集站点 | 如"马来西亚" |
| 产品线 | 如"手机云台" |
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

## 注意事项

1. **CDP 模式**：需要先在 Chrome 中登录知虾，之后自动复用登录状态
2. **Playwright 模式**：首次运行需扫码登录，之后自动复用 cookies
3. **验证码**：脚本会自动尝试关闭验证码弹窗
4. **反爬限制**：建议设置合理的采集间隔
5. **数据量**：根据账号等级，单次导出可能有数量限制

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| CDP Proxy 未就绪 | 检查 Chrome 远程调试是否开启 |
| 登录失败 | 在 Chrome 中手动登录知虾网站 |
| 导出失败 | 检查页面选择器是否更新 |
| 数据为空 | 确认关键词有搜索结果 |
| 下载失败 | 检查下载目录权限 |

## 版本历史

- v3.1 (2025-06) - 添加 CDP 模式，复用 Chrome 登录状态
- v3.0 (2025-06) - 重构采集流程，优化登录管理
- v2.0 (2024-01) - 添加数据处理和飞书推送
- v1.0 (2024-01) - 初始版本