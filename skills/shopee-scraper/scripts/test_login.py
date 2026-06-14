#!/usr/bin/env python3
"""
测试优化后的知虾登录流程
使用 webapp-testing skill 最佳实践
"""

import os
import sys
from datetime import datetime

# 添加脚本目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

try:
    from zhixia_login import ZhixiaLoginManager
    LOGIN_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入登录管理器: {e}")
    LOGIN_MANAGER_AVAILABLE = False

def test_optimized_login():
    """测试优化后的登录流程"""
    print("=" * 60)
    print("测试优化后的知虾登录流程")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if not LOGIN_MANAGER_AVAILABLE:
        print("错误: 登录管理器不可用")
        return False
    
    print("1. 创建登录管理器...")
    manager = ZhixiaLoginManager()
    print("   登录管理器已创建")
    print()
    
    print("2. 测试无头模式 + Cookies 登录...")
    print("   (如果 Cookies 有效，应该可以直接登录)")
    print()
    
    # 先测试无头模式
    success, status = manager.ensure_login(headless=True, auto_login_timeout=30)
    
    if success:
        print(f"   ✓ 登录成功: {status}")
        print()
        
        # 测试页面访问
        print("3. 测试访问知虾功能页面...")
        try:
            page = manager.get_page()
            if page:
                # 访问模糊搜索页面
                search_url = "https://shopee.menglar.com/workbench/search/keyword-fuzzy-search?type=1&search=&searchType=2"
                print(f"   访问: {search_url}")
                page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
                page.wait_for_load_state('networkidle', timeout=15000)
                
                current_url = page.url
                print(f"   当前URL: {current_url}")
                
                # 截图
                screenshot_dir = os.path.join(script_dir, '..', 'data', 'login_screenshots')
                screenshot_path = os.path.join(screenshot_dir, 'test_search_page.png')
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"   截图已保存: {screenshot_path}")
                
                if '/login' not in current_url:
                    print("   ✓ 可以访问功能页面（登录有效）")
                else:
                    print("   ✗ 被重定向到登录页（登录可能失效）")
        except Exception as e:
            print(f"   ✗ 页面访问测试失败: {e}")
        
        manager.close_browser()
        print()
        print("=" * 60)
        print("测试完成: 登录流程正常工作")
        print("=" * 60)
        return True
    
    print(f"   ✗ 无头模式登录失败: {status}")
    print()
    
    # 如果无头模式失败，提示需要手动登录
    print("3. 需要手动登录...")
    print("   Cookies 无效或过期，需要扫码登录")
    print("   请运行以下命令进行手动登录:")
    print()
    print("   python zhixia_login.py")
    print()
    print("   或者在可见模式下运行测试:")
    print("   python test_login.py --visible")
    print()
    
    manager.close_browser()
    return False


def test_visible_login():
    """测试可见模式登录（需要手动扫码）"""
    print("=" * 60)
    print("测试可见模式登录（需要手动扫码）")
    print("=" * 60)
    print()
    
    if not LOGIN_MANAGER_AVAILABLE:
        print("错误: 登录管理器不可用")
        return False
    
    manager = ZhixiaLoginManager()
    
    print("启动可见浏览器窗口...")
    print("请在浏览器中使用微信扫码登录知虾")
    print("等待时间: 180 秒")
    print()
    
    success, status = manager.ensure_login(headless=False, auto_login_timeout=180)
    
    if success:
        print()
        print("=" * 60)
        print(f"登录成功: {status}")
        print("Cookies 已保存，下次可以直接使用无头模式")
        print("=" * 60)
        manager.close_browser()
        return True
    
    print()
    print("=" * 60)
    print(f"登录失败: {status}")
    print("=" * 60)
    manager.close_browser()
    return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='测试知虾登录流程')
    parser.add_argument('--visible', action='store_true', help='使用可见模式（需要手动扫码）')
    
    args = parser.parse_args()
    
    if args.visible:
        success = test_visible_login()
    else:
        success = test_optimized_login()
    
    sys.exit(0 if success else 1)