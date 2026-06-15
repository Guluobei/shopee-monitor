#!/usr/bin/env python3
"""
导出知虾数据 - 使用Playwright下载捕获
"""
import os
import sys
import time
from pathlib import Path

# 添加脚本目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

def run_export():
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("知虾数据导出 - Playwright下载捕获模式")
    print("=" * 60)

    # 读取配置
    config_path = os.path.join(script_dir, '..', 'config', 'competitors.yaml')
    import yaml
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 设置下载目录
    download_dir = os.path.join(script_dir, '..', 'data', 'downloads')
    os.makedirs(download_dir, exist_ok=True)

    with sync_playwright() as p:
        # 启动浏览器
        print("\n1. 启动浏览器...")
        browser = p.chromium.launch(
            headless=False,  # 非headless模式可见
            args=['--disable-blink-features=AutomationControlled']
        )

        # 创建带下载功能的上下文
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            accept_downloads=True,
        )

        page = context.new_page()

        # 注入脚本隐藏自动化特征
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        print("\n2. 访问知虾...")
        page.goto("https://shopee.menglar.com/workbench/search/keyword-fuzzy-search?type=1&search=insta360%20flow%202&searchType=2", wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        print(f"当前URL: {page.url}")
        page.screenshot(path="/tmp/export_pw1.png")
        print("截图: /tmp/export_pw1.png")

        # 等待页面加载完成
        print("\n3. 等待页面加载...")
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except:
            print("networkidle超时，继续...")
        time.sleep(2)

        # 点击导出按钮
        print("\n4. 点击导出按钮...")

        # 方法1: 通过文本查找
        export_clicked = False
        try:
            # 查找包含"导出"的按钮
            export_btn = page.get_by_text("导出", exact=False).first
            if export_btn:
                export_btn.click(timeout=5000)
                print("通过文本找到并点击导出按钮")
                export_clicked = True
        except Exception as e:
            print(f"方法1失败: {e}")

        if not export_clicked:
            try:
                # 方法2: 通过class查找
                page.click("button:has-text('导出')", timeout=5000)
                print("通过CSS找到并点击导出按钮")
                export_clicked = True
            except Exception as e:
                print(f"方法2失败: {e}")

        if not export_clicked:
            try:
                # 方法3: 查找所有按钮并点击最后一个
                btns = page.query_selector_all("button")
                for btn in btns:
                    text = btn.inner_text()
                    if "导出" in text:
                        btn.click()
                        print(f"点击按钮: {text}")
                        export_clicked = True
                        break
            except Exception as e:
                print(f"方法3失败: {e}")

        time.sleep(2)
        page.screenshot(path="/tmp/export_pw2.png")
        print("截图: /tmp/export_pw2.png")

        # 填写序号范围并确认导出
        print("\n5. 填写序号范围...")

        # 使用JavaScript直接操作DOM
        page.evaluate("""
            () => {
                // 查找输入框
                const inputs = document.querySelectorAll('input');
                let count = 0;
                for (let input of inputs) {
                    // 尝试找到序号输入框
                    const parent = input.closest('div') || input.parentElement;
                    if (parent && parent.textContent && parent.textContent.includes('序号')) {
                        if (count === 0) input.value = '1';
                        else if (count === 1) input.value = '10';
                        count++;
                        if (count >= 2) break;
                    }
                }
                // 如果没找到，尝试所有文本输入框
                if (count < 2) {
                    const textInputs = document.querySelectorAll('input[type="text"], input:not([type])');
                    textInputs.forEach((input, idx) => {
                        if (idx === 0) input.value = '1';
                        else if (idx === 1) input.value = '10';
                    });
                }
            }
        """)

        time.sleep(1)

        # 点击确认导出
        print("\n6. 点击确认导出...")

        try:
            confirm_btn = page.get_by_text("确认导出", exact=False).first
            confirm_btn.click(timeout=5000)
            print("已点击确认导出")
        except Exception as e:
            print(f"点击确认导出失败: {e}")
            # 尝试其他方法
            try:
                page.click("button:has-text('确认')", timeout=3000)
                print("通过确认按钮点击")
            except:
                pass

        time.sleep(3)
        page.screenshot(path="/tmp/export_pw3.png")
        print("截图: /tmp/export_pw3.png")

        # 检查是否触发了下载
        print("\n" + "=" * 60)
        print("请检查:")
        print("1. 浏览器中是否弹出下载对话框?")
        print("2. 或者文件已经下载到默认目录?")
        print("=" * 60)

        # 等待一段时间看是否有下载
        print("\n等待下载完成（30秒）...")
        time.sleep(30)

        # 列出下载目录
        print("\n检查下载目录:")
        if os.path.exists(download_dir):
            files = os.listdir(download_dir)
            if files:
                print(f"找到 {len(files)} 个文件:")
                for f in files:
                    fpath = os.path.join(download_dir, f)
                    print(f"  - {f} ({os.path.getsize(fpath)} bytes)")
            else:
                print("下载目录为空")
        else:
            print("下载目录不存在")

        # 截图
        page.screenshot(path="/tmp/export_pw_final.png")
        print(f"\n最终截图: /tmp/export_pw_final.png")

        browser.close()
        print("\n浏览器已关闭")

if __name__ == '__main__':
    run_export()
