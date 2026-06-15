# 三件事情详细操作指南

---

## 第一件事：有了映射表后，每次下载处理数据怎么做

### 1.1 映射表是什么？

你的项目中有两个关键映射表：

**① 配置映射表** `config/competitors.yaml`
- 站点代码 → 国家名称（MY→马来西亚）
- 产品线代码 → 关键词组合（OP→insta360 luna ultra）

**② 列名映射表** `scripts/data_processor.py` 中的 `COLUMN_MAPPINGS`
- 知虾导出的各种列名 → 标准列名
- 例如：'价格'、'售价'、'price'、'Price' 都映射到标准字段 '价格'

### 1.2 每次处理数据的完整步骤

#### 步骤一：采集数据

```powershell
# 进入脚本目录
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper

# 运行采集（指定站点和产品线）
python scripts/zhixia_monitor.py collect --sites MY ID --product-lines OP OM
```

**采集过程**：
- 脚本自动读取 `competitors.yaml` 获取关键词
- 按站点+产品线组合搜索
- 导出Excel保存到 `data/downloads/`

#### 步骤二：处理数据

```powershell
# 运行数据处理脚本
python scripts/data_processor.py
```

**处理过程**：
1. 扫描 `data/downloads/` 目录找到所有Excel文件
2. 读取Excel，通过 `COLUMN_MAPPINGS` 识别列名
3. 标准化列名（统一为标准字段）
4. 清洗数值（处理货币符号、千分位、"万"单位）
5. 添加元数据（站点名称、产品线名称、采集日期）
6. 去重（按商品名称+店铺）
7. 计算指标（销量占比、价格偏离度）
8. 输出CSV到 `output/`

#### 步骤三：查看结果

```powershell
# 查看输出的CSV
Get-ChildItem output -Filter *.csv

# 查看数据摘要
Get-Content output\consolidated\summary_*.json | ConvertFrom-Json
```

### 1.3 映射表如何生效？

| 映射表 | 生效时机 | 作用 |
|--------|----------|------|
| competitors.yaml | 采集阶段 | 决定搜索哪些关键词 |
| COLUMN_MAPPINGS | 处理阶段 | 将知虾列名转为标准列名 |

**示例**：
- 知虾导出列名可能是 "商品价格" 或 "售价"
- 映射表将其统一转为标准列名 "价格"
- 后续分析脚本只需要处理标准列名

---

## 第二件事：自动化跑数据验证

### 2.1 自动化配置

#### 方式一：TRAE定时任务（推荐）

使用Schedule工具创建定时任务：

```
任务名称：Shopee竞品日报
执行时间：每天 09:00（北京时间）
cron表达式：0 9 * * *
timezone：Asia/Shanghai
执行内容：
  运行Shopee竞品数据采集：
  1. 采集站点：MY、ID、TH
  2. 产品线：OP、OM
  3. 运行data_processor清洗数据
  4. 输出到 c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper\output
  5. 如果记录数<100，发送告警提醒
```

#### 方式二：PowerShell脚本

```powershell
# 创建自动化脚本
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper

# 采集
python scripts/zhixia_monitor.py collect --sites MY ID TH --product-lines OP OM

# 处理
python scripts/data_processor.py

# 验证（检查记录数）
$summary = Get-Content output\consolidated\summary_*.json | ConvertFrom-Json
if ($summary.'数据概况'.'总记录数' -lt 100) {
    Write-Host "警告：数据量不足！"
}
```

### 2.2 验证检查清单

#### 采集阶段验证

| 检查项 | 如何检查 | 正常标准 | 异常处理 |
|--------|----------|----------|----------|
| 登录状态 | 查看 `data/cookies.json` | 文件存在且有效 | 手动扫码登录 |
| 下载文件 | `Get-ChildItem data\downloads` | 有新Excel文件 | 检查关键词是否有结果 |
| 采集日志 | 查看 `logs/collect_*.json` | status=success | 查看error字段 |
| 验证码 | 检查日志是否有验证码记录 | 无验证码记录 | 手动处理验证码 |

#### 处理阶段验证

| 检查项 | 如何检查 | 正常标准 | 异常处理 |
|--------|----------|----------|----------|
| 文件读取 | 查看日志"找到X个Excel文件" | 文件数>0 | 检查下载目录 |
| 列名识别 | 查看日志是否有"缺少必要列" | 无警告 | 更新COLUMN_MAPPINGS |
| 数据清洗 | 检查CSV数值字段 | 无异常值 | 调整clean_numeric |
| 去重效果 | 查看日志"去重移除了X条" | 合理数量 | 调整去重规则 |

#### 输出阶段验证

| 检查项 | 如何检查 | 正常标准 |
|--------|----------|----------|
| CSV生成 | `Get-ChildItem output\*.csv` | 文件存在 |
| 摘要生成 | `Get-Content output\consolidated\summary_*.json` | JSON格式正确 |
| 记录数 | 查看摘要中的"总记录数" | >预期数量 |
| 站点覆盖 | 查看摘要中的"涉及站点" | 与采集站点一致 |

### 2.3 验证脚本示例

```powershell
# 完整验证脚本
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper

# 1. 检查下载文件数量
$downloads = Get-ChildItem data\downloads -Filter *.xlsx
Write-Host "下载文件数: $($downloads.Count)"

# 2. 检查输出文件
$outputs = Get-ChildItem output -Filter *.csv
Write-Host "输出CSV数: $($outputs.Count)"

# 3. 检查摘要数据
$summary = Get-Content output\consolidated\summary_*.json | ConvertFrom-Json
Write-Host "总记录数: $($summary.'数据概况'.'总记录数')"
Write-Host "涉及站点: $($summary.'数据概况'.'涉及站点')"
Write-Host "涉及产品线: $($summary.'数据概况'.'涉及产品线')"

# 4. 验证必要字段
$csv = Import-Csv output\shopee_competitor_data_*.csv
$emptyNames = ($csv | Where-Object { $_.'商品名称' -eq '' }).Count
Write-Host "空商品名称数: $emptyNames"

# 5. 基本质量判断
if ($summary.'数据概况'.'总记录数' -ge 100 -and $emptyNames -eq 0) {
    Write-Host "验证通过！"
} else {
    Write-Host "验证失败，请检查数据！"
}
```

---

## 第三件事：录入飞书验证

### 3.1 飞书推送方式选择

| 方式 | 适用场景 | 优点 | 缺点 |
|------|----------|------|------|
| Webhook机器人 | 发送日报卡片到群聊 | 简单快速 | 只能发送消息 |
| 多维表格(Base) | 持久化存储数据 | 可查询、可分析 | 需要配置表格 |

### 3.2 Webhook推送步骤

#### 步骤一：配置Webhook

1. 在飞书群聊添加机器人
2. 获取Webhook URL
3. 编辑 `config/competitors.yaml`：

```yaml
feishu:
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
```

#### 步骤二：生成飞书卡片

```powershell
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\report-generator

# 生成卡片
python scripts/report_builder.py --input ../shopee-scraper/output/consolidated/summary_*.json
```

#### 步骤三：发送到飞书

```powershell
python scripts/feishu_sender.py --webhook <webhook_url>
```

#### 步骤四：验证发送结果

| 验证项 | 检查方法 | 正常标准 |
|--------|----------|----------|
| 发送成功 | 查看飞书群聊 | 收到卡片消息 |
| 内容完整 | 检查卡片内容 | 与摘要数据一致 |
| 格式正确 | 检查卡片渲染 | 无乱码、无错位 |

### 3.3 多维表格录入步骤

#### 步骤一：创建飞书多维表格

1. 在飞书创建新的多维表格
2. 设置字段：
   - 采集日期（日期）
   - 站点（文本）
   - 产品线（文本）
   - 商品名称（文本）
   - 店铺名称（文本）
   - 价格（数字）
   - 销量（数字）
   - 评分（数字）
   - 商品链接（超链接）

#### 步骤二：获取表格信息

- app_token：表格的唯一标识
- table_id：数据表的ID

#### 步骤三：使用lark-base skill录入

```
将CSV数据写入飞书多维表格：
- CSV文件：c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper\output\shopee_competitor_data_*.csv
- 目标表格：[app_token]/[table_id]
- 映射字段：CSV列名 → 表格字段名
```

#### 步骤四：验证录入结果

| 验证项 | 检查方法 | 正常标准 |
|--------|----------|----------|
| 记录写入 | 查看表格记录数 | 与CSV记录数一致 |
| 字段映射 | 检查各字段内容 | 数据正确对应 |
| 格式正确 | 检查数字、日期格式 | 格式正确显示 |

### 3.4 飞书录入验证脚本

```powershell
# 验证飞书推送结果

# 方式1：检查Webhook响应
# 发送成功会返回 {"code":0,"msg":"success"}

# 方式2：检查多维表格记录数
# 使用lark-base skill查询表格记录数，与CSV对比

# 示例验证逻辑
$csvRecords = (Import-Csv output\shopee_competitor_data_*.csv).Count
Write-Host "CSV记录数: $csvRecords"

# 如果使用多维表格，查询表格记录数
# 预期：表格记录数 = CSV记录数
```

---

## 三件事情的关系

```
第一件事（每次处理）─────────────────────────────→
    ↓                                              │
    采集 → 清洗 → 输出CSV                          │
                                                   │
第二件事（自动化验证）────────────────────────────→
    ↓                                              │
    定时执行 + 检查数据质量                         │
                                                   │
第三件事（录入飞书）─────────────────────────────→
    ↓                                              │
    推送卡片 / 写入多维表格 + 验证                  │
                                                   │
───────────────────────────────────────────────────→
              完整闭环流程
```

---

## 快速参考

| 事情 | 核心命令 | 输出位置 |
|------|----------|----------|
| 第一件事 | `python zhixia_monitor.py collect` + `python data_processor.py` | `output/*.csv` |
| 第二件事 | Schedule定时任务 + 验证脚本 | `logs/*.json` |
| 第三件事 | `python feishu_sender.py` 或 lark-base skill | 飞书群聊/多维表格 |