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
- **智能登录**：自动检测登录状态，支持扫码登录
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

### 命令行

```powershell
# 测试模式（单站点单关键词）
python run_daily.py test

# 完整采集（所有站点所有产品线）
python run_daily.py full

# 自定义采集
python run_daily.py run --sites MY ID --product-lines OP OM

# 无头模式
python run_daily.py run --sites MY --headless
```

### Agent调用

```
采集Shopee马来西亚站点的云台产品数据
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
│       ├── zhixia_scraper.py  # 采集器
│       ├── zhixia_login.py    # 登录管理
│       ├── zhixia_monitor.py  # 监控主程序
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
pip install playwright pandas pyyaml openpyxl
playwright install chromium
```

## 注意事项

1. **登录状态**：首次运行需扫码登录，之后自动复用cookies
2. **验证码**：脚本会自动尝试关闭验证码弹窗
3. **反爬限制**：建议设置合理的采集间隔
4. **数据量**：根据账号等级，单次导出可能有数量限制

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| 登录失败 | 手动登录知虾，保存cookies |
| 导出失败 | 检查页面选择器是否更新 |
| 数据为空 | 确认关键词有搜索结果 |
| 下载失败 | 检查下载目录权限 |

## 版本历史

- v3.0 (2025-06) - 重构采集流程，优化登录管理
- v2.0 (2024-01) - 添加数据处理和飞书推送
- v1.0 (2024-01) - 初始版本