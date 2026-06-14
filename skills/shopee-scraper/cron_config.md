# Shopee竞品监控系统 - 定时任务配置

## Cron表达式说明

```
┌───────────── 分钟 (0 - 59)
│ ┌───────────── 小时 (0 - 23)
│ │ ┌───────────── 日 (1 - 31)
│ │ │ ┌───────────── 月 (1 - 12)
│ │ │ │ ┌───────────── 星期 (0 - 6) (周日=0)
│ │ │ │ │
* * * * *
```

## 推荐配置

### 方案1: 每天早上8点执行（推荐）
```bash
# 每天早上8点执行完整流程
0 8 * * * cd /path/to/shopee-monitor && python scripts/zhixia_monitor.py run >> logs/cron.log 2>&1
```

### 方案2: 工作日早上8点执行（仅工作日）
```bash
# 周一至周五早上8点执行
0 8 * * 1-5 cd /path/to/shopee-monitor && python scripts/zhixia_monitor.py run >> logs/cron.log 2>&1
```

### 方案3: 每天分时段执行
```bash
# 早上8点采集
0 8 * * * cd /path/to/shopee-monitor && python scripts/zhixia_monitor.py collect >> logs/cron_collect.log 2>&1

# 早上9点处理
0 9 * * * cd /path/to/shopee-monitor && python scripts/zhixia_monitor.py process >> logs/cron_process.log 2>&1
```

## 安装Cron任务

### 1. 编辑crontab
```bash
crontab -e
```

### 2. 添加任务
```bash
# 知虾竞品监控 - 每日早上8点
0 8 * * * cd /home/user/shopee-monitor && /usr/bin/python3 scripts/zhixia_monitor.py run >> logs/cron.log 2>&1
```

### 3. 验证任务
```bash
# 查看当前cron任务
crontab -l

# 查看cron日志
tail -f /var/log/syslog | grep CRON
```

## 定时任务管理脚本

```bash
#!/bin/bash
# manage_cron.sh - Cron任务管理脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_JOB="0 8 * * * cd $SCRIPT_DIR && python3 scripts/zhixia_monitor.py run >> logs/cron.log 2>&1"

case "$1" in
    add)
        (crontab -l 2>/dev/null | grep -v "zhixia_monitor.py"; echo "$CRON_JOB") | crontab -
        echo "Cron任务已添加"
        ;;
    remove)
        crontab -l 2>/dev/null | grep -v "zhixia_monitor.py" | crontab -
        echo "Cron任务已移除"
        ;;
    list)
        crontab -l | grep "zhixia_monitor.py"
        ;;
    status)
        if crontab -l 2>/dev/null | grep -q "zhixia_monitor.py"; then
            echo "Cron任务状态: 已启用"
            crontab -l | grep "zhixia_monitor.py"
        else
            echo "Cron任务状态: 未启用"
        fi
        ;;
    *)
        echo "用法: $0 {add|remove|list|status}"
        ;;
esac
```

## Windows任务计划程序

### 创建任务步骤

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器：每日，8:00
4. 设置操作：启动程序
   - 程序: `pythonw.exe`
   - 参数: `scripts/zhixia_monitor.py run`
   - 起始位置: `C:\path\to\shopee-monitor`

### PowerShell脚本

```powershell
# schedule_task.ps1 - Windows任务计划程序配置

$action = New-ScheduledTaskAction `
    -Execute "pythonw.exe" `
    -Argument "scripts\zhixia_monitor.py run" `
    -WorkingDirectory "C:\path\to\shopee-monitor"

$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "8:00AM"

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName "Shopee竞品监控" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "每日采集Shopee竞品数据"
```

## 监控定时任务执行

### 检查执行日志
```bash
# 查看最近执行日志
tail -50 logs/cron.log

# 查看今天的执行情况
grep "$(date +%Y-%m-%d)" logs/cron.log

# 检查是否有错误
grep -i "error\|failed\|exception" logs/cron.log
```

### 钉钉/飞书通知（可选）

```python
# notify.py - 执行完成后发送通知
import requests

def send_notification(title: str, content: str, webhook_url: str):
    """发送通知到钉钉或飞书"""
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "content": f"### {title}\n\n{content}"
        }
    }
    requests.post(webhook_url, json=data)
```
