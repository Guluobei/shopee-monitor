# Shopee竞品数据流程指南

> 从知虾/虾多拉采集 → 数据清洗 → 分析 → 推送飞书

---

## 一、整体流程概览

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   数据采集      │ → │   数据清洗      │ → │   数据分析      │ → │   推送飞书      │
│  (知虾/虾多拉)  │    │  (标准化处理)   │    │  (生成报告)     │    │  (录入验证)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 二、有了映射表后，每次下载处理数据的步骤

### 2.1 映射表的作用

映射表定义在 `config/competitors.yaml`，包含：
- **站点映射**：MY、ID、TH、PH、SG、VN → 国家名称
- **产品线映射**：OP、OM、MIC → 关键词组合
- **列名映射**：知虾导出的各种列名 → 标准列名（见 `data_processor.py` 的 `COLUMN_MAPPINGS`）

### 2.2 每次数据处理的完整步骤

#### 步骤1：数据采集

```powershell
# 进入脚本目录
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper

# 运行采集脚本
python scripts/zhixia_monitor.py collect --sites MY ID --product-lines OP OM
```

**采集流程**：
1. 自动检测知虾登录状态
2. 按站点+产品线组合搜索关键词
3. 等待搜索结果加载
4. 点击导出按钮下载Excel
5. 保存到 `data/downloads/` 目录

#### 步骤2：数据清洗处理

```powershell
# 运行数据处理脚本
python scripts/data_processor.py --download-dir data/downloads --output-dir output
```

**处理流程**：
1. **读取Excel** → 自动识别列名（通过映射表）
2. **标准化列名** → 统一为标准字段名
3. **清洗数值** → 处理货币符号、千分位、"万"单位等
4. **添加元数据** → 站点名称、产品线名称、采集日期
5. **去重** → 按商品名称+店铺去重
6. **计算指标** → 销量占比、价格偏离度等
7. **导出CSV** → 标准格式输出

#### 步骤3：验证数据质量

```powershell
# 查看生成的摘要文件
type output\consolidated\summary_YYYYMMDD.json
```

**验证要点**：
| 检查项 | 预期结果 | 异常处理 |
|--------|----------|----------|
| 总记录数 | > 0 | 检查关键词是否有搜索结果 |
| 涉及站点数 | 与采集站点数一致 | 检查是否有站点采集失败 |
| 必要字段完整性 | 商品名称、价格、销量非空 | 检查列名映射是否正确 |
| 数据去重效果 | 无重复记录 | 调整去重规则 |

---

## 三、自动化跑数据验证流程

### 3.1 定时采集配置

使用TRAE的Schedule功能设置定时任务：

```yaml
# 每天早上9点采集
cron_expression: "0 9 * * *"
timezone: "Asia/Shanghai"
message: |
  运行Shopee竞品数据采集：
  1. 采集站点：MY、ID、TH
  2. 产品线：OP、OM
  3. 数据清洗并生成CSV报告
  4. 输出到 c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper\output
```

### 3.2 自动化验证检查清单

#### 采集阶段验证

| 验证点 | 检查方法 | 失败处理 |
|--------|----------|----------|
| 登录状态 | 检查cookies.json是否存在且有效 | 手动扫码登录 |
| 页面加载 | 检查截图文件 | 增加等待时间 |
| 导出按钮 | 检查下载目录是否有新文件 | 更新选择器 |
| 验证码弹窗 | 检查日志是否有验证码记录 | 手动处理 |

#### 处理阶段验证

| 验证点 | 检查方法 | 失败处理 |
|--------|----------|----------|
| 文件读取 | 检查日志"找到X个Excel文件" | 检查下载目录 |
| 列名识别 | 检查日志是否有"缺少必要列"警告 | 更新COLUMN_MAPPINGS |
| 数据清洗 | 检查CSV中数值字段格式 | 调整clean_numeric函数 |
| 去重效果 | 检查日志"去重移除了X条" | 调整key_columns |

### 3.3 验证脚本示例

```powershell
# 检查采集结果
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper

# 1. 检查下载文件
Get-ChildItem data\downloads -Filter *.xlsx | Measure-Object

# 2. 检查输出CSV
Get-ChildItem output -Filter *.csv | Measure-Object

# 3. 检查日志
Get-Content logs\collect_*.json | ConvertFrom-Json | Select-Object status, records_count

# 4. 验证数据完整性
python scripts/data_processor.py --download-dir data/downloads --no-full-export
```

---

## 四、录入飞书验证流程

### 4.1 飞书推送方式

**方式1：Webhook机器人（推荐）**
- 配置群聊机器人获取Webhook URL
- 发送卡片消息到群聊

**方式2：多维表格（Base）**
- 创建飞书多维表格存储数据
- 通过API批量写入记录

### 4.2 飞书录入验证步骤

#### 步骤1：配置飞书参数

编辑 `config/competitors.yaml`：
```yaml
feishu:
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
  # 或使用App认证
  app_id: "cli_xxx"
  app_secret: "xxx"
```

#### 步骤2：生成飞书卡片

```powershell
# 运行报告生成脚本
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\report-generator
python scripts/report_builder.py --input ../shopee-scraper/output/consolidated/summary_*.json
```

#### 步骤3：发送到飞书

```powershell
python scripts/feishu_sender.py --card output/feishu_card.json --webhook <webhook_url>
```

#### 步骤4：验证录入结果

| 验证点 | 检查方法 |
|--------|----------|
| 消息发送成功 | 检查飞书群聊是否收到卡片 |
| 数据完整性 | 卡片内容与摘要数据一致 |
| 格式正确 | 卡片渲染正常，无乱码 |

### 4.3 飞书多维表格录入（可选）

如果需要将数据持久化存储到飞书多维表格：

1. **创建多维表格**
   - 在飞书创建新的多维表格
   - 设置字段：站点、产品线、商品名称、价格、销量、采集日期等

2. **配置表格Token**
   - 获取表格的app_token和table_id
   - 配置到 `competitors.yaml`

3. **批量写入数据**
   ```
   使用lark-base skill将CSV数据写入飞书多维表格
   ```

---

## 五、完整自动化流程示例

### 每日自动化任务配置

```
任务名称：Shopee竞品日报
执行时间：每天09:00（北京时间）
执行内容：
  1. 采集MY、ID、TH三个站点的OP、OM产品线数据
  2. 运行data_processor清洗数据
  3. 生成CSV报告和摘要JSON
  4. 构建飞书卡片并发送到监控群
  5. 验证：检查数据记录数>100，否则发送告警
输出目录：c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper\output
```

### 手动触发验证

```powershell
# 完整流程一键执行
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper

# 1. 采集
python scripts/zhixia_monitor.py collect --sites MY ID --product-lines OP

# 2. 处理
python scripts/data_processor.py

# 3. 验证输出
Get-Content output\consolidated\summary_*.json | ConvertFrom-Json

# 4. 推送飞书（如已配置）
cd ..\report-generator
python scripts/feishu_sender.py
```

---

## 六、常见问题排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 采集数据为空 | 关键词无搜索结果 | 检查关键词是否正确 |
| 列名无法识别 | 知虾更新了导出格式 | 更新COLUMN_MAPPINGS |
| 数值清洗失败 | 特殊格式未处理 | 扩展clean_numeric函数 |
| 飞书发送失败 | Webhook失效或网络问题 | 检查Webhook配置 |
| 数据重复 | 去重规则不适用 | 调整key_columns参数 |

---

## 七、关键文件说明

| 文件 | 作用 | 位置 |
|------|------|------|
| `competitors.yaml` | 站点、产品线、关键词配置 | `config/` |
| `COLUMN_MAPPINGS` | 列名映射表（代码内） | `data_processor.py` |
| `cookies.json` | 知虾登录状态 | `data/` |
| `summary_*.json` | 数据摘要报告 | `output/consolidated/` |
| `shopee_competitor_data_*.csv` | 清洗后的完整数据 | `output/` |

---

**总结**：整个流程是"采集→清洗→分析→推送"四步闭环。映射表确保数据标准化，自动化验证保证数据质量，飞书推送实现结果可视化。