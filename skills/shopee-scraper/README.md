# Shopee竞品监控系统

基于知虾（shopee.menglar.com）的Shopee东南亚站点竞品数据自动采集系统。

## 功能特性

- 🌏 **多站点支持**: 支持东南亚6个Shopee站点（MY/ID/TH/PH/SG/VN）
- 📦 **多产品线**: 支持OP云台、OM支架、MIC麦克风等多种产品线
- 🔍 **智能搜索**: 基于关键词的模糊搜索
- 📥 **自动导出**: 自动点击导出按钮下载Excel文件
- 📊 **数据处理**: 自动解析、合并、去重数据
- ⏰ **定时任务**: 支持配置每日自动执行

## 快速开始

### 1. 安装依赖

```bash
# 克隆项目
cd /workspace/shopee-monitor/skills/shopee-scraper

# 安装Python依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium --with-deps
```

### 2. 配置监控参数

编辑 `config/competitors.yaml` 文件，配置你要监控的产品线和关键词：

```yaml
product_lines:
  OP:
    name: "手机云台/稳定器"
    keywords:
      - "insta360 luna ultra"
```

### 3. 运行测试

```bash
# 查看系统状态
python scripts/zhixia_monitor.py status

# 运行完整流程
python scripts/zhixia_monitor.py run

# 仅采集数据
python scripts/zhixia_monitor.py collect --sites MY ID

# 仅处理数据
python scripts/zhixia_monitor.py process
```

## 使用方法

### 命令行参数

```bash
# 完整流程
python zhixia_monitor.py run \
  --sites MY ID TH \
  --product-lines OP OM \
  --format csv

# 仅采集
python zhixia_monitor.py collect \
  --sites MY \
  --headless

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
```

## 配置文件说明

### 产品线配置

```yaml
product_lines:
  OP:                           # 产品线代码
    name: "手机云台/稳定器"       # 产品线名称
    keywords:                   # 搜索关键词列表
      - "insta360 luna ultra"
      - "insta360 ace"
    min_price: null            # 最低价格（可选）
    max_price: null            # 最高价格（可选）
```

### 站点配置

```yaml
sites:
  - code: MY
    name: 马来西亚
  - code: ID
    name: 印度尼西亚
  # ...
```

## 输出文件

### CSV报告格式

| 字段 | 说明 |
|------|------|
| 采集日期 | 数据采集日期 |
| 采集站点 | 如"马来西亚" |
| 商品名称 | 商品标题 |
| 店铺名称 | 店铺名称 |
| 价格 | 当前售价 |
| 销量 | 累计销量 |
| 月销量 | 月销量 |
| 评价数 | 评价数量 |
| 评分 | 商品评分 |

### 文件位置

```
output/
├── shopee_competitor_data_20240115_120000.csv  # CSV报告
├── consolidated/
│   └── summary_20240115.json                   # 数据摘要
└── logs/
    └── pipeline_*.json                        # 运行日志
```

## 定时任务

### 设置每日自动执行

```bash
# 编辑crontab
crontab -e

# 添加定时任务（每天早上8点执行）
0 8 * * * cd /path/to/shopee-monitor && python scripts/zhixia_monitor.py run
```

详细配置请参考 `cron_config.md`

## 项目结构

```
shopee-monitor/
├── SKILL.md                     # Skill定义文档
├── README.md                    # 项目说明
├── requirements.txt              # Python依赖
├── install.sh                    # 安装脚本
├── cron_config.md                # 定时任务配置
├── config/
│   └── competitors.yaml          # 配置文件
└── scripts/
    ├── __init__.py
    ├── zhixia_monitor.py        # 主程序
    ├── zhixia_scraper.py        # 浏览器爬虫
    └── data_processor.py        # 数据处理器
```

## 依赖说明

- Python 3.8+
- playwright >= 1.40.0
- pandas >= 2.0.0
- pyyaml >= 6.0
- openpyxl >= 3.1.0

## 注意事项

1. **登录状态**: 运行前请确保知虾账号已登录
2. **验证码**: 如遇验证码弹窗，脚本会自动尝试关闭
3. **下载目录**: 确保下载目录有写入权限
4. **数据量**: 根据账号等级不同，单次导出可能有数量限制

## 故障排查

### 常见问题

1. **无法导入playwright**: 运行 `pip install playwright && playwright install chromium`
2. **导出按钮找不到**: 页面结构可能已更新，需更新选择器
3. **下载失败**: 检查下载目录权限

### 调试模式

```bash
# 使用非无头模式查看浏览器操作
python scripts/zhixia_monitor.py collect
```

## License

MIT License
