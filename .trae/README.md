# Shopee竞品情报套件 - Trae/OpenCode 版本

> 一键采集东南亚6国竞品数据，自动生成分析报告

## 安装方法

### Trae/OpenCode 用户

将 `.trae/skills/` 目录复制到你的 Trae skills 目录：

```powershell
# 复制主套件
Copy-Item -Path ".trae\skills\shopee-competitor-suite" -Destination "$env:USERPROFILE\.trae-cn\skills\" -Recurse

# 复制采集器子 Skill
Copy-Item -Path ".trae\skills\shopee-scraper" -Destination "$env:USERPROFILE\.trae-cn\skills\" -Recurse
```

### 依赖安装

```powershell
pip install playwright pandas pyyaml openpyxl requests
```

## 使用方法

### CDP 模式（推荐）

复用 Chrome 浏览器登录状态：

```powershell
# 进入脚本目录
cd $env:USERPROFILE\.trae-cn\skills\shopee-scraper\scripts

# 检查 CDP Proxy 状态
python run_daily.py check

# 自定义采集
python run_daily.py cdp --sites MY ID --keyword insta360

# 完整采集
python run_daily.py cdp
```

### 前置条件

1. Chrome 浏览器已开启远程调试
2. 已在 Chrome 中登录知虾网站 (shopee.menglar.com)
3. CDP Proxy 已启动 (localhost:3456)

## 文件结构

```
.trae/skills/
├── shopee-competitor-suite/    # 主 Skill
│   └── SKILL.md
├── shopee-scraper/             # 数据采集子 Skill
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── run_daily.py        # 统一入口
│   │   ├── zhixia_cdp_scraper.py  # CDP采集器
│   │   └── zhixia_scraper.py   # Playwright采集器
│   │   └── zhixia_login.py     # 登录管理
│   ├── config/
│   │   └── competitors.yaml    # 配置文件
│   └── data/
│       └ downloads/            # 下载目录
│       └ cookies.json          # 会话状态（不推送）
```

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

## 安全说明

- **不会存储账号密码**：只保存会话 cookies
- **敏感文件已排除**：cookies.json、下载文件不推送 GitHub
- **遇到验证码会暂停**：等待用户手动处理

## 版本历史

- v3.2 (2026-06) - Trae/OpenCode 格式、批次导出、断点续传
- v3.1 (2025-06) - CDP 模式，复用 Chrome 登录状态
- v3.0 (2025-06) - 重构采集流程