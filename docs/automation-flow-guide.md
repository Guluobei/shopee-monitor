# 知虾自动化下载流程 - 完整操作指南

---

## 流程概览

```
打开网站 → 登录(扫码/Cookies) → 切换站点 → 搜索关键词 → 导出下载 → 循环下一站点
```

---

## 一、现有脚本说明

| 脚本 | 功能 | 关键方法 |
|------|------|----------|
| `zhixia_login.py` | 登录管理 | `ensure_login()` 智能登录 |
| `zhixia_scraper.py` | 数据采集 | `run_scrape()` 执行采集 |
| `zhixia_monitor.py` | 主程序 | `collect()` 采集+处理 |

---

## 二、跑通流程的步骤

### 步骤1：首次登录（保存Cookies）

```powershell
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper

# 运行登录测试（会弹出浏览器窗口，等待扫码）
python scripts/zhixia_login.py
```

**流程说明**：
1. 脚本启动浏览器（可见模式）
2. 导航到知虾工作台 `https://shopee.menglar.com/workbench/home`
3. 如果未登录，会跳转到登录页显示二维码
4. **你需要在浏览器窗口中用微信扫码登录**
5. 登录成功后自动保存Cookies到 `data/cookies.json`
6. 浏览器保持打开状态

### 步骤2：验证登录状态

```powershell
# 检查Cookies是否保存成功
Get-Content data\cookies.json | ConvertFrom-Json | Measure-Object

# 查看登录截图
Get-ChildItem data\login_screenshots
```

### 步骤3：测试单站点采集

```powershell
# 测试采集马来西亚站点的OP产品线（可见模式，方便观察）
python scripts/zhixia_monitor.py collect --sites MY --product-lines OP
```

**采集流程**：
```
1. 启动浏览器（尝试用Cookies登录）
2. 如果Cookies无效 → 弹出窗口等待扫码
3. 登录成功后 → 进入模糊搜索页面
4. 搜索关键词 "insta360 luna ultra"
5. 点击导出按钮 → 下载Excel
6. 保存到 data/downloads/MY_OP_insta360_luna_ultra_20260615.xlsx
```

### 步骤4：测试多站点采集

```powershell
# 采集马来西亚和印尼两个站点
python scripts/zhixia_monitor.py collect --sites MY ID --product-lines OP
```

**多站点流程**：
```
站点MY:
  → 搜索 "insta360 luna ultra" → 导出 → MY_OP_xxx.xlsx
站点ID:
  → 切换站点 → 搜索 "insta360 luna ultra" → 导出 → ID_OP_xxx.xlsx
```

### 步骤5：查看采集结果

```powershell
# 查看下载的文件
Get-ChildItem data\downloads -Filter "*.xlsx"

# 查看采集日志
Get-Content logs\collect_*.json | ConvertFrom-Json
```

---

## 三、自动化流程详解

### 3.1 打开网站

**代码实现** (`zhixia_login.py`):
```python
# 导航到工作台页面
self.page.goto('https://shopee.menglar.com/workbench/home', wait_until='domcontentloaded', timeout=30000)
```

**关键点**：
- 直接访问工作台URL（而非首页）
- 如果已登录 → 显示工作台
- 如果未登录 → 自动跳转到登录页

### 3.2 登录流程

**智能登录策略** (`zhixia_login.py` 的 `ensure_login()`):

```
阶段1: 无头模式 + Cookies
  → 启动无头浏览器
  → 加载 cookies.json
  → 访问工作台检查登录状态
  → 如果成功 → 保持登录，继续采集
  → 如果失败 → 关闭无头浏览器

阶段2: 可见模式 + 手动扫码
  → 启动可见浏览器
  → 等待用户扫码登录（最长180秒）
  → 登录成功 → 保存Cookies → 继续采集
```

**登录检测逻辑**：
```python
# 检查URL是否包含登录特征
LOGIN_URL_PATTERNS = ['/login', 'signin', 'passport', 'auth']

# 如果URL包含这些 → 未登录
# 如果URL包含 'workbench' 且不含登录特征 → 已登录
```

### 3.3 切换站点

**代码实现** (`zhixia_scraper.py` 的 `select_site()`):

```python
# 站点映射
site_map = {
    'MY': '马来西亚',
    'ID': '印尼',
    'TH': '泰国',
    'PH': '菲律宾',
    'SG': '新加坡',
    'VN': '越南',
}

# 点击站点链接
self.page.click(f'a:has-text("{site_name}")')
```

**实际操作**：
- 知虾页面底部有站点列表
- 点击目标站点名称即可切换

### 3.4 搜索产品

**代码实现** (`zhixia_scraper.py` 的 `search_keyword()`):

```python
# 直接通过URL访问搜索结果
search_url = f"{base_url}/workbench/search/keyword-fuzzy-search?type=1&search={encoded_keyword}&searchType=2"
self.navigate_to(search_url)
```

**关键参数**：
- `type=1` → 搜索类型
- `search=` → 关键词（URL编码）
- `searchType=2` → 搜索模式

### 3.5 导出下载

**代码实现** (`zhixia_scraper.py` 的 `export_data()`):

```python
# 点击导出按钮
self.page.click('button:has-text("导出")')

# 输入序号范围（1-500）
inputs[0].fill('1')  # 最小序号
inputs[1].fill('500')  # 最大序号

# 点击确认导出
self.page.click('button:has-text("确认导出")')

# 等待下载完成
time.sleep(10)
```

---

## 四、完整自动化命令

### 4.1 采集指定站点和产品线

```powershell
# 采集马来西亚、印尼、泰国的OP和OM产品线
python scripts/zhixia_monitor.py collect --sites MY ID TH --product-lines OP OM
```

### 4.2 采集所有站点和产品线

```powershell
# 采集全部（使用配置文件中的所有站点和产品线）
python scripts/zhixia_monitor.py collect
```

### 4.3 完整流程（采集+处理）

```powershell
# 运行完整流程：采集 → 处理 → 输出CSV
python scripts/zhixia_monitor.py run --sites MY ID --product-lines OP
```

---

## 五、常见问题处理

### 问题1：登录失败

**现象**：浏览器弹出但无法登录

**解决方案**：
```powershell
# 1. 删除旧Cookies重新登录
Remove-Item data\cookies.json

# 2. 强制可见模式重新扫码
python scripts/zhixia_login.py
```

### 问题2：站点切换失败

**现象**：搜索结果还是上一个站点的数据

**解决方案**：
- 检查知虾页面底部的站点列表是否可见
- 可能需要更新 `select_site()` 的选择器

### 问题3：导出按钮找不到

**现象**：脚本提示"未找到导出按钮"

**解决方案**：
```powershell
# 查看调试截图
Get-ChildItem data\login_screenshots\export_debug.png

# 可能需要更新导出按钮选择器
```

### 问题4：下载文件未生成

**现象**：导出按钮点击成功但没有文件

**解决方案**：
- 检查下载目录权限
- 检查知虾账号是否有导出权限
- 增加等待时间 `time.sleep(15)`

---

## 六、自动化流程验证清单

| 步骤 | 验证方法 | 成功标志 |
|------|----------|----------|
| 1.打开网站 | 查看截图 | `login_screenshots/check_login_*.png` 显示工作台 |
| 2.登录 | 查看Cookies | `data/cookies.json` 文件存在且非空 |
| 3.切换站点 | 查看日志 | 日志显示"站点切换成功" |
| 4.搜索产品 | 查看截图 | 页面显示搜索结果 |
| 5.导出下载 | 查看文件 | `data/downloads/` 有新Excel文件 |
| 6.多站点循环 | 查看文件数 | 文件数 = 站点数 × 产品线数 × 关键词数 |

---

## 七、下一步：设置定时自动化

跑通流程后，可以设置定时任务：

```
任务名称：Shopee竞品每日采集
执行时间：每天 09:00
执行内容：
  cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper
  python scripts/zhixia_monitor.py collect --sites MY ID TH --product-lines OP OM
  python scripts/data_processor.py
```

---

## 快速测试命令

```powershell
# 1. 进入目录
cd c:\Users\Administrator\Documents\Trae\shopee-competitor-suite\skills\shopee-scraper

# 2. 首次登录（扫码）
python scripts/zhixia_login.py

# 3. 测试单站点采集
python scripts/zhixia_monitor.py collect --sites MY --product-lines OP

# 4. 查看结果
Get-ChildItem data\downloads
Get-Content logs\collect_*.json | ConvertFrom-Json
```