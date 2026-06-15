---
name: shopee-scraper
description: Shopee竞品数据采集：从知虾平台采集东南亚6国竞品价格和销量数据
triggers:
  - "采集Shopee数据"
  - "抓取马来西亚云台产品"
  - "导出OP产品线数据"
  - "运行知虾采集"
  - "采集东南亚竞品"
  - "Shopee数据采集"
standalone: true
---

# Shopee竞品数据采集

> 从知虾平台自动化采集东南亚6国Shopee竞品数据

## 功能

- **多站点支持**：马来西亚、印尼、泰国、菲律宾、新加坡、越南
- **多产品线**：OP（云台）、OM（支架）、MIC（麦克风）等
- **智能登录**：自动检测登录状态，支持扫码登录
- **自动导出**：点击导出按钮下载Excel文件
- **验证码处理**：自动尝试关闭验证码弹窗

## 使用方法

### Agent调用

```
采集Shopee马来西亚站点的云台产品数据
```

```
采集马来西亚和印尼的OP、OM产品线数据
```

### 命令行

```powershell
# 运行完整采集
python scripts/zhixia_monitor.py collect --sites MY ID --product-lines OP

# 仅采集指定站点
python scripts/zhixia_scraper.py --sites MY --product-lines OP

# 查看状态
python scripts/zhixia_monitor.py status
```

## 输出

- **Excel文件**：保存在 `data/downloads/` 目录
- **文件命名**：`{站点}_{产品线}_{关键词}_{日期}.xlsx`
- **日志文件**：保存在 `logs/` 目录

## 输出字段

| 字段 | 说明 |
|------|------|
| 商品名称 | 商品标题 |
| 店铺名称 | 店铺名 |
| 价格 | 当前售价 |
| 原价 | 原价（如有） |
| 销量 | 累计销量 |
| 评分 | 商品评分 |
| 商品链接 | 详情页URL |

## 配置

配置文件位于 `config/competitors.yaml`：

```yaml
sites:
  - code: MY
    name: 马来西亚
  - code: ID
    name: 印度尼西亚
  # ...

product_lines:
  OP:
    name: "手机云台/稳定器"
    keywords:
      - "insta360 luna ultra"
  # ...
```

## 安全边界

- **不会修改或删除**任何现有文件
- **遇到验证码时暂停**，等待用户处理
- **不会泄露**账号密码

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| 登录失败 | 手动登录知虾，保存cookies |
| 导出失败 | 检查页面选择器是否更新 |
| 数据为空 | 确认关键词有搜索结果 |

## 文件结构

```
shopee-scraper/
├── SKILL.md
├── config/
│   └ competitors.yaml
├── scripts/
│   ├── zhixia_monitor.py
│   ├── zhixia_scraper.py
│   ├── zhixia_login.py
│   └ data_processor.py
├── data/
│   ├── downloads/
│   ├── cookies.json
│   └ login_screenshots/
├── logs/
├── output/
```