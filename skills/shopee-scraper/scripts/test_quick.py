#!/usr/bin/env python3
"""
快速测试脚本 - 测试知虾采集器
"""

import os
import sys

# 添加脚本目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from zhixia_scraper import ZhixiaScraper

def quick_test():
    """快速测试采集器功能"""
    print("=" * 60)
    print("知虾采集器快速测试")
    print("=" * 60)

    # 创建采集器
    config_path = os.path.join(script_dir, '..', 'config', 'competitors.yaml')
    scraper = ZhixiaScraper(config_path=config_path)

    # 首先用headless模式检查是否已登录
    print("\n1. 检查登录状态...")
    logged_in = scraper.launch_browser(headless=True)

    if not logged_in:
        print("\n检测到未登录，需要进行登录授权")
        print("将启动可见浏览器进行微信扫码登录...")

        # 关闭当前浏览器
        scraper.close_browser()

        # 以非headless模式启动
        scraper.launch_browser(headless=False)

        # 等待用户登录
        if scraper.wait_for_manual_login(timeout=180):
            print("登录成功!")
            # 截图确认
            scraper.page.screenshot(path="/tmp/zhixia_logged_in.png")
            print("登录后截图已保存")
        else:
            print("登录超时!")
            scraper.close_browser()
            return

    # 已登录，测试功能
    print("\n2. 测试访问知虾...")
    scraper.navigate_to(scraper.config['zhixia']['base_url'])
    print(f"当前URL: {scraper.page.url}")
    scraper.page.screenshot(path="/tmp/zhixia_home.png")

    print("\n3. 测试进入模糊搜索...")
    scraper.go_to_fuzzy_search()
    print(f"当前URL: {scraper.page.url}")
    scraper.page.screenshot(path="/tmp/fuzzy_search.png")

    print("\n4. 测试搜索关键词...")
    scraper.search_keyword("insta360 flow 2")
    print(f"当前URL: {scraper.page.url}")
    scraper.page.screenshot(path="/tmp/search_result.png")

    print("\n5. 关闭浏览器...")
    scraper.close_browser()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    print("\n提示:")
    print("- Cookies已保存，下次运行可直接使用headless模式")
    print("- 查看 /tmp/ 目录下的截图确认页面状态")

if __name__ == '__main__':
    quick_test()
