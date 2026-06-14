# Shopee竞品监控系统 (Shopee Scraper Skill)

## 概述

这是一个用于自动采集Shopee竞品数据的OpenCode Skill。通过知虾（shopee.menglar.com）平台，自动化获取东南亚六国（马来西亚、印尼、泰国、菲律宾、新加坡、越南）的竞品价格和销量数据。

## 功能特性

- **多站点支持**: 支持东南亚6个Shopee站点
- **多产品线**: 支持OP（云台）、OM（支架）、MIC（麦克风）等多种产品线
- **智能搜索**: 基于关键词的模糊搜索
- **自动导出**: 自动点击导出按钮下载Excel文件
- **数据处理**: 自动解析、合并、去重数据
- **定时任务**: 支持配置每日自动执行

## 支持的市场

| 代码 | 国家 | Shopee域名 |
|------|------|------------|
| MY | 马来西亚 | shopee.com.my |
| ID | 印度尼西亚 | shopee.co.id |
| TH | 泰国 | shopee.co.th |
| PH | 菲律宾 | shopee.ph |
| SG | 新加坡 | shopee.sg |
| VN | 越南 | shopee.vn |

## 配置说明

### 产品线配置 (config/competitors.yaml)

```yaml
# 产品线及对应关键词
product_lines:
  OP:
    name: "手机云台/稳定器"
    keywords:
      - "insta360 luna ultra"
  OM:
    name: "手机支架/智能跟随"
    keywords:
      - "insta360 flow 2"
      - "hohem"
      - "zhiyun"
  MIC_400_1000:
    name: "麦克风 400-1000价位"
    keywords:
      - "hollyland mic"
    min_price: 400
    max_price: 1000
  MIC_1000PLUS:
    name: "麦克风 1000+价位"
    keywords:
      - "insta360 mic pro"
      - "hollyland"
      - "saramonic"
      - "rode"
```

## 使用方法

### 命令行使用

```bash
# 运行完整流程（采集+处理）
python zhixia_monitor.py run

# 仅采集数据
python zhixia_monitor.py collect --sites MY ID

# 仅处理已有数据
python zhixia_monitor.py process

# 查看状态
python zhixia_monitor.py status

# 清理旧文件
python zhixia_monitor.py clean --days 7
```

### OpenCode Agent调用

```
请帮我运行Shopee竞品数据采集：
1. 采集马来西亚和印尼站点的OP产品线数据
2. 处理采集的数据并生成CSV报告
3. 将报告发送到飞书
```

## 文件结构

```
shopee-monitor/
├── SKILL.md                    # Skill定义文档
├── config/
│   └── competitors.yaml        # 配置文件
├── scripts/
│   ├── zhixia_monitor.py      # 主程序
│   ├── zhixia_scraper.py      # 浏览器爬虫
│   └── data_processor.py      # 数据处理器
├── data/
│   └── downloads/             # 下载的Excel文件
└── output/
    ├── shopee_competitor_data_*.csv  # 输出CSV
    ├── consolidated/         # 合并数据
    └── logs/                  # 运行日志
```

## 输出格式

### CSV列说明

| 列名 | 说明 |
|------|------|
| 采集日期 | 数据采集日期 |
| 采集站点 | 如"马来西亚" |
| 站点代码 | 如"MY" |
| 产品线 | 如"手机云台/稳定器" |
| 产品线代码 | 如"OP" |
| 搜索关键词 | 搜索时使用的关键词 |
| 商品名称 | 商品标题 |
| 店铺名称 | 店铺名称 |
| 价格 | 当前售价 |
| 原价 | 原价（如果有） |
| 销量 | 累计销量 |
| 月销量 | 月销量（如果有） |
| 评价数 | 评价/评论数量 |
| 评分 | 商品/店铺评分 |
| 商品ID | Shopee商品ID |
| 商品链接 | 商品详情页链接 |

## 定时任务配置

### 每日自动执行

可以通过系统定时任务（如cron）配置每日自动执行：

```bash
# 每天早上8点执行
0 8 * * * cd /path/to/shopee-monitor && python scripts/zhixia_monitor.py run
```

## 依赖说明

- Python 3.8+
- playwright
- pandas
- pyyaml
- openpyxl (用于读取Excel)

### 安装依赖

```bash
pip install playwright pandas pyyaml openpyxl
playwright install chromium
```

## 注意事项

1. **登录状态**: 运行前请确保知虾账号已登录，浏览器会自动复用登录状态
2. **验证码**: 如遇验证码弹窗，脚本会自动尝试关闭
3. **下载目录**: 确保下载目录有写入权限
4. **反爬限制**: 建议设置合理的采集间隔，避免触发反爬机制
5. **数据量**: 根据账号等级不同，单次导出可能有数量限制

## 故障排查

### 常见问题

1. **无法登录**: 检查cookies是否过期，可手动登录后重新运行
2. **导出按钮找不到**: 页面结构可能已更新，需更新选择器
3. **下载失败**: 检查下载目录权限和网络连接
4. **数据为空**: 确认关键词在目标市场有搜索结果

### 调试模式

```bash
# 启用详细日志
python zhixia_monitor.py collect --verbose

# 使用非无头模式查看浏览器操作
python zhixia_monitor.py collect
```

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      OpenCode Agent                        │
│                    (自然语言指令解析)                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      zhixia_monitor.py                     │
│                      (主程序/调度器)                         │
└─────────────────────────────────────────────────────────────┘
                    │                       │
                    ▼                       ▼
┌──────────────────────────┐   ┌──────────────────────────────┐
│    zhixia_scraper.py     │   │    data_processor.py         │
│    (浏览器自动化采集)      │   │    (数据解析处理)             │
│                          │   │                              │
│  ┌────────────────────┐  │   │  ┌────────────────────────┐   │
│  │ Playwright        │  │   │  │ Excel读取              │   │
│  │ 浏览器控制         │  │   │  │ 列名标准化             │   │
│  └────────────────────┘  │   │  │ 数据清洗               │   │
│  ┌────────────────────┐  │   │  │ 去重合并               │   │
│  │ 知虾网站交互       │  │   │  │ 市场指标计算           │   │
│  │ 站点切换          │  │   │  └────────────────────────┘   │
│  │ 关键词搜索        │  │   │                              │
│  │ 数据导出          │  │   │                              │
│  └────────────────────┘  │   │                              │
└──────────────────────────┘   └──────────────────────────────┘
                    │                       │
                    ▼                       ▼
┌──────────────────────────┐   ┌──────────────────────────────┐
│    Excel文件             │   │    CSV报告                   │
│    (知虾导出)            │   │    (最终输出)                 │
└──────────────────────────┘   └──────────────────────────────┘
```

## 版本历史

- v1.0.0 (2024-01) - 初始版本，支持基础采集和处理功能
