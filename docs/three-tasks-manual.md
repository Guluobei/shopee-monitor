# 三件事情操作手册

---

## 第一件事：有了映射表，每次如何快速打标

### 什么是"打标"？

打标 = 数据标准化处理，包括：
- 列名标准化（知虾各种列名 → 统一标准列名）
- 站点标记（MY → 马来西亚）
- 产品线标记（OP → 手机云台/稳定器）
- 数据清洗（数值格式、去重）

### 映射表在哪里？

| 映射表 | 文件位置 | 作用 |
|--------|----------|------|
| 站点/产品线映射 | `config/competitors.yaml` | 站点代码→国家名，产品线代码→产品名 |
| 列名映射 | `scripts/data_processor.py` 的 `COLUMN_MAPPINGS` | 知虾列名→标准列名 |

### 快速打标操作

#### 方法一：一键处理（推荐）

```powershell
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper

# 一键处理所有下载的Excel文件
python scripts/data_processor.py
```

**自动完成**：
1. 扫描 `data/downloads/` 所有Excel
2. 读取并识别列名（通过映射表）
3. 标准化列名
4. 添加站点、产品线、日期标记
5. 清洗数值、去重
6. 输出到 `output/`

#### 方法二：指定文件处理

```powershell
# 只处理特定文件
python scripts/data_processor.py --download-dir data/downloads --output-dir output
```

#### 方法三：Python代码调用

```python
from scripts.data_processor import DataProcessor

processor = DataProcessor()

# 处理所有文件
results = processor.run_process()

# 或只处理指定文件
files = ['data/downloads/MY_OP_insta360_20260615.xlsx']
merged_df = processor.merge_all_data(files)
processor.export_to_csv(merged_df)
```

### 打标后的输出字段

| 标准字段 | 来源 | 说明 |
|----------|------|------|
| 采集日期 | 文件名解析 | 20260615 |
| 采集站点 | 映射表 | MY → 马来西亚 |
| 站点代码 | 文件名解析 | MY |
| 产品线 | 映射表 | OP → 手机云台/稳定器 |
| 产品线代码 | 文件名解析 | OP |
| 搜索关键词 | 文件名解析 | insta360 luna ultra |
| 商品名称 | 列名映射 | 原列可能是"标题"、"name"等 |
| 价格 | 列名映射 | 原列可能是"售价"、"price"等 |
| 销量 | 列名映射 | 原列可能是"已售"、"sold"等 |

### 如何更新映射表？

#### 更新列名映射（知虾更新了导出格式）

编辑 `scripts/data_processor.py`：

```python
COLUMN_MAPPINGS = {
    '商品名称': ['商品名称', '产品名称', '商品标题', '标题', 'name', 'Name', 'product_name'],
    '价格': ['价格', '商品价格', '售价', 'price', 'Price', 'current_price'],
    # 添加新的列名变体...
    '新字段': ['知虾新列名', 'other_variant'],
}
```

#### 更新站点/产品线映射

编辑 `config/competitors.yaml`：

```yaml
product_lines:
  NEW_LINE:
    name: "新产品线名称"
    keywords:
      - "关键词1"
      - "关键词2"
```

---

## 第二件事：如何每天自动化下载

### 方案一：TRAE定时任务（推荐）

#### 创建定时任务

使用Schedule工具，配置如下：

```
任务名称：Shopee竞品每日采集
执行时间：每天 09:00（北京时间）
cron表达式：0 9 * * *
timezone：Asia/Shanghai
执行内容：
  运行Shopee竞品数据采集任务：
  1. 进入目录：c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper
  2. 采集站点：MY、ID、TH
  3. 产品线：OP、OM
  4. 运行 python scripts/zhixia_monitor.py collect --sites MY ID TH --product-lines OP OM
  5. 运行 python scripts/data_processor.py 进行数据打标
  6. 输出文件保存到 output 目录
  7. 如果采集记录数<50，发送告警提醒
```

#### 任务执行流程

```
09:00 自动触发
    ↓
检查登录状态（cookies.json）
    ↓
按站点+产品线组合搜索
    ↓
导出Excel到 data/downloads/
    ↓
运行data_processor打标
    ↓
输出CSV到 output/
    ↓
生成摘要JSON
```

### 方案二：Windows任务计划

#### 创建PowerShell脚本

```powershell
# 保存为 daily_collect.ps1
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper

# 采集
python scripts/zhixia_monitor.py collect --sites MY ID TH --product-lines OP OM

# 打标
python scripts/data_processor.py

# 验证
$summary = Get-Content output\consolidated\summary_*.json | ConvertFrom-Json
Write-Log "采集完成，记录数: $($summary.'数据概况'.'总记录数')"
```

#### 配置Windows任务计划

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器：每天 09:00
4. 操作：启动程序 `powershell.exe`
5. 参数：`-File "C:\...\daily_collect.ps1"`

### 方案三：Python定时脚本

```python
# schedule_runner.py
import schedule
import time
import subprocess

def daily_job():
    subprocess.run([
        'python', 'scripts/zhixia_monitor.py', 'collect',
        '--sites', 'MY', 'ID', 'TH',
        '--product-lines', 'OP', 'OM'
    ])
    subprocess.run(['python', 'scripts/data_processor.py'])

schedule.every().day.at("09:00").do(daily_job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 自动化下载的注意事项

| 注意点 | 说明 | 处理方式 |
|--------|------|----------|
| 登录状态 | cookies可能过期 | 定期手动登录刷新 |
| 验证码 | 可能触发验证码 | 脚本会暂停，需手动处理 |
| 采集间隔 | 避免触发反爬 | 设置合理间隔（建议每天一次） |
| 数据量限制 | 账号等级限制导出数量 | 分多次采集或升级账号 |

### 自动化下载验证

```powershell
# 检查今日采集结果
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper

# 1. 查看下载文件（按日期筛选）
Get-ChildItem data\downloads -Filter "*$(Get-Date -Format 'yyyyMMdd')*.xlsx"

# 2. 查看输出CSV
Get-ChildItem output -Filter "*$(Get-Date -Format 'yyyyMMdd')*.csv"

# 3. 查看摘要
$todaySummary = "output\consolidated\summary_$(Get-Date -Format 'yyyyMMdd').json"
if (Test-Path $todaySummary) {
    Get-Content $todaySummary | ConvertFrom-Json
}
```

---

## 第三件事：将分析结果推送到飞书

### 推送方式选择

| 方式 | 适用场景 | 配置难度 |
|------|----------|----------|
| Webhook机器人 | 发送日报卡片到群聊 | 简单 |
| 多维表格(Base) | 持久化存储，支持查询分析 | 中等 |
| 飞书文档 | 生成详细分析报告 | 中等 |

### 方式一：Webhook机器人推送

#### 步骤1：获取Webhook URL

1. 打开飞书群聊
2. 点击"设置" → "群机器人" → "添加机器人"
3. 选择"自定义机器人"
4. 复制Webhook URL

#### 步骤2：配置Webhook

编辑 `config/competitors.yaml`：

```yaml
feishu:
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx"
```

#### 步骤3：生成推送内容

```powershell
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\report-generator

# 从摘要生成飞书卡片
python scripts/report_builder.py --input ../shopee-scraper/output/consolidated/summary_*.json --format feishu
```

#### 步骤4：发送到飞书

```powershell
# 发送卡片
python scripts/feishu_sender.py --webhook "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
```

#### 飞书卡片内容示例

```json
{
  "msg_type": "interactive",
  "card": {
    "header": {
      "title": { "tag": "plain_text", "content": "Shopee竞品日报 - 2026-06-15" },
      "template": "blue"
    },
    "elements": [
      { "tag": "div", "text": { "tag": "lark_md", "content": "**数据概况**\n总记录数: 1,234条\n涉及站点: 3个\n涉及产品线: 2个" }},
      { "tag": "div", "text": { "tag": "lark_md", "content": "**站点分布**\n马来西亚: 456条\n印尼: 389条\n泰国: 389条" }},
      { "tag": "action", "actions": [{ "tag": "button", "text": { "tag": "plain_text", "content": "查看详情" }, "url": "https://..." }]}
    ]
  }
}
```

### 方式二：多维表格(Base)推送

#### 步骤1：创建多维表格

在飞书创建多维表格，设置字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 采集日期 | 日期 | 数据采集日期 |
| 站点 | 文本 | 国家名称 |
| 产品线 | 文本 | 产品线名称 |
| 商品名称 | 文本 | 商品标题 |
| 店铺名称 | 文本 | 店铺名 |
| 价格 | 数字 | 商品价格 |
| 销量 | 数字 | 销售数量 |
| 评分 | 数字 | 商品评分 |
| 商品链接 | 超链接 | 详情页URL |

#### 步骤2：获取表格Token

- app_token：表格URL中的唯一标识
- table_id：数据表ID

#### 步骤3：使用lark-base skill写入

```
将CSV数据写入飞书多维表格：
- CSV文件路径：c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper\output\shopee_competitor_data_*.csv
- 目标表格：app_token = xxx, table_id = xxx
- 字段映射：
  - 采集日期 → 采集日期
  - 采集站点 → 站点
  - 产品线 → 产品线
  - 商品名称 → 商品名称
  - 价格 → 价格
  - 销量 → 销量
```

#### 步骤4：验证写入结果

使用lark-base skill查询表格记录数，与CSV对比：

```
查询飞书多维表格记录数：
- app_token: xxx
- table_id: xxx
- 预期记录数：与CSV文件行数一致
```

### 方式三：飞书文档推送

#### 步骤1：生成HTML报告

```powershell
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\report-generator

python scripts/report_builder.py --input ../shopee-scraper/output/consolidated/summary_*.json --format html
```

#### 步骤2：使用lark-doc skill创建文档

```
创建飞书文档，内容为竞品分析报告：
- 标题：Shopee竞品日报 - 2026-06-15
- 内容来源：HTML报告文件
- 包含：数据概况、站点分析、产品线分析、热销榜单
```

### 推送验证清单

| 验证项 | 检查方法 | 正常标准 |
|--------|----------|----------|
| Webhook发送 | 查看群聊消息 | 收到卡片 |
| 卡片内容 | 检查数据 | 与摘要一致 |
| 多维表格写入 | 查询记录数 | = CSV行数 |
| 字段映射 | 检查各字段 | 数据正确对应 |

---

## 三件事情完整流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        每日自动化流程                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  09:00 定时触发                                                  │
│      ↓                                                          │
│  ┌─────────────────┐                                            │
│  │ 第二件事        │  自动下载                                   │
│  │ zhixia_monitor  │  → 采集MY/ID/TH的OP/OM数据                  │
│  │ collect         │  → 导出Excel到downloads/                   │
│  └─────────────────┘                                            │
│      ↓                                                          │
│  ┌─────────────────┐                                            │
│  │ 第一件事        │  快速打标                                   │
│  │ data_processor  │  → 读取Excel，通过映射表标准化               │
│  │                 │  → 添加站点、产品线、日期标记                 │
│  │                 │  → 输出CSV和摘要JSON                        │
│  └─────────────────┘                                            │
│      ↓                                                          │
│  ┌─────────────────┐                                            │
│  │ 第三件事        │  推送飞书                                   │
│  │ feishu_sender   │  → 生成飞书卡片                             │
│  │ 或 lark-base    │  → 发送到群聊 / 写入多维表格                 │
│  └─────────────────┘                                            │
│      ↓                                                          │
│  验证：记录数>50，否则告警                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 快速命令参考

| 事情 | 命令 | 输出 |
|------|------|------|
| 第一件事：打标 | `python data_processor.py` | `output/*.csv` + `summary_*.json` |
| 第二件事：下载 | `python zhixia_monitor.py collect --sites MY ID --product-lines OP` | `data/downloads/*.xlsx` |
| 第三件事：推送 | `python feishu_sender.py` 或 lark-base skill | 飞书群聊/多维表格 |

---

## 需要的配置文件

| 配置项 | 文件 | 需要填写 |
|--------|------|----------|
| 站点/产品线 | `config/competitors.yaml` | 已配置 |
| 列名映射 | `scripts/data_processor.py` | 已配置（可扩展） |
| 飞书Webhook | `config/competitors.yaml` | 需填写webhook_url |
| 飞书多维表格 | 手动获取 | app_token, table_id |