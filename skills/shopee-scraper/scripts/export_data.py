#!/usr/bin/env python3
"""
导出知虾数据 - 捕获下载文件
"""
import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from zhixia_scraper import ZhixiaScraper
import time

def export_with_download():
    print("=" * 60)
    print("知虾数据导出 - 下载捕获模式")
    print("=" * 60)

    config_path = os.path.join(script_dir, '..', 'config', 'competitors.yaml')
    scraper = ZhixiaScraper(config_path=config_path)

    try:
        # 启动浏览器（headless=False以可见模式）
        print("\n1. 启动浏览器...")
        scraper.launch_browser(headless=False)

        # 访问搜索页面
        print("\n2. 访问搜索页面...")
        scraper.navigate_to("https://shopee.menglar.com/workbench/search/keyword-fuzzy-search?type=1&search=insta360%20flow%202&searchType=2")
        time.sleep(3)

        # 截图确认
        scraper.page.screenshot(path="/tmp/export_step1.png")
        print("截图已保存: /tmp/export_step1.png")

        # 点击导出按钮
        print("\n3. 点击导出按钮...")
        selectors = [
            "button:has-text('导出')",
            "[class*='export']",
            "[class*='导出']",
            ".export-btn"
        ]

        export_btn = None
        for sel in selectors:
            try:
                export_btn = scraper.page.wait_for_selector(sel, timeout=3000)
                if export_btn:
                    print(f"找到导出按钮: {sel}")
                    break
            except:
                continue

        if export_btn:
            export_btn.click()
            print("已点击导出按钮")
        else:
            print("未找到导出按钮，尝试使用JavaScript点击")
            scraper.page.evaluate("document.querySelector('button').click()")

        time.sleep(2)
        scraper.page.screenshot(path="/tmp/export_step2.png")

        # 查找并点击确认导出按钮
        print("\n4. 点击确认导出...")
        time.sleep(1)

        # 使用JavaScript直接执行导出
        scraper.page.evaluate("""
            // 填写序号范围
            const inputs = document.querySelectorAll('input[type="text"]');
            if (inputs.length >= 2) {
                inputs[0].value = '1';
                inputs[1].value = '10';
            }
        """)

        # 查找确认按钮
        confirm_selectors = [
            "button:has-text('确认导出')",
            "button:has-text('导出')",
            "[class*='confirm']"
        ]

        for sel in confirm_selectors:
            try:
                btn = scraper.page.wait_for_selector(sel, timeout=2000)
                if btn:
                    print(f"找到确认按钮: {sel}")
                    btn.click()
                    print("已点击确认导出")
                    break
            except:
                continue

        time.sleep(5)
        scraper.page.screenshot(path="/tmp/export_step3.png")

        print("\n" + "=" * 60)
        print("请检查浏览器窗口，导出对话框是否已关闭？")
        print("如果文件已开始下载，请在浏览器下载目录中查找")
        print("=" * 60)

        # 保持浏览器打开一段时间
        print("\n等待10秒后关闭...")
        time.sleep(10)

        scraper.close_browser()

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        try:
            scraper.close_browser()
        except:
            pass

if __name__ == '__main__':
    export_with_download()
