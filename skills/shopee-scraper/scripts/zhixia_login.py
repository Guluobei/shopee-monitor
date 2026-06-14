#!/usr/bin/env python3
"""
知虾登录模块 - 使用 webapp-testing skill 最佳实践
优化网页登录流程，支持智能登录检测和自动化处理

v2 修复：
- 修复 check_login_status 导航到公开首页导致误判
- 修复登录后浏览器被关闭的问题
- 修复切换站点后 session 丢失的问题
- 避免频繁开关浏览器导致账号被锁
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from playwright.sync_api import TimeoutError as PlaywrightTimeout

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ZhixiaLoginManager:
    """知虾登录管理器 - 使用 webapp-testing 最佳实践"""
    
    # URL 常量
    BASE_URL = 'https://shopee.menglar.com'
    WORKBENCH_URL = 'https://shopee.menglar.com/workbench/home'
    
    # 登录相关的 URL 特征（在 URL 中出现这些表示未登录）
    LOGIN_URL_PATTERNS = ['/login', 'signin', 'passport', 'auth']
    
    def __init__(self, config: Dict = None, cookie_file: str = None, screenshot_dir: str = None):
        """
        初始化登录管理器
        
        Args:
            config: 配置字典，包含 zhixia 相关配置
            cookie_file: Cookie 保存路径
            screenshot_dir: 截图保存目录
        """
        self.config = config or {
            'zhixia': {
                'base_url': self.BASE_URL,
                'login_url': self.WORKBENCH_URL
            }
        }
        
        # Cookie 文件路径
        self.cookie_file = cookie_file or os.path.join(
            os.path.dirname(__file__), '..', 'data', 'cookies.json'
        )
        os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
        
        # 截图目录（用于调试）
        self.screenshot_dir = screenshot_dir or os.path.join(
            os.path.dirname(__file__), '..', 'data', 'login_screenshots'
        )
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # Playwright 对象
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # 登录状态标记
        self._is_logged_in = False
        self._login_attempts = 0
        self._max_login_attempts = 2  # 最多尝试登录 2 次，避免频繁登录
    
    def _take_screenshot(self, name: str) -> str:
        """保存截图用于调试"""
        if not self.page:
            return ""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}.png"
        filepath = os.path.join(self.screenshot_dir, filename)
        
        try:
            self.page.screenshot(path=filepath, full_page=True)
            logger.info(f"截图已保存: {filepath}")
            return filepath
        except Exception as e:
            logger.warning(f"截图保存失败: {e}")
            return ""
    
    def launch_browser(self, headless: bool = True) -> bool:
        """
        启动浏览器
        
        Args:
            headless: 是否使用无头模式
            
        Returns:
            是否成功启动
        """
        # 如果已有浏览器在运行，先关闭
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass
        
        logger.info("正在启动浏览器...")
        
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                ]
            )
            
            # 创建上下文
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                accept_downloads=True,
            )
            
            # 注入脚本隐藏自动化特征
            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
            """)
            
            self.page = self.context.new_page()
            self._is_logged_in = False
            logger.info("浏览器启动成功")
            return True
            
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            return False
    
    def close_browser(self, save_cookies: bool = True) -> None:
        """关闭浏览器"""
        try:
            if save_cookies and self.context:
                try:
                    self._save_cookies_internal()
                except Exception as e:
                    logger.warning(f"保存 Cookies 时出错: {e}")
            
            if self.browser:
                try:
                    self.browser.close()
                except Exception as e:
                    logger.warning(f"关闭浏览器时出错: {e}")
            
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception as e:
                    logger.warning(f"停止 Playwright 时出错: {e}")
            
            self.browser = None
            self.context = None
            self.page = None
            self.playwright = None
            self._is_logged_in = False
            
            logger.info("浏览器已关闭")
        except Exception as e:
            logger.warning(f"关闭浏览器时出错: {e}")
    
    def _save_cookies_internal(self) -> bool:
        """内部保存 cookies"""
        if not self.context:
            return False
        
        try:
            cookies = self.context.cookies()
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"Cookies 已保存到: {self.cookie_file}")
            return True
        except Exception as e:
            logger.warning(f"保存 Cookies 失败: {e}")
            return False
    
    def save_cookies(self) -> bool:
        """公开保存 cookies 接口"""
        return self._save_cookies_internal()
    
    def load_cookies(self) -> bool:
        """从文件加载 cookies"""
        if not self.context or not os.path.exists(self.cookie_file):
            return False
        
        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            if not cookies:
                logger.info("Cookies 文件为空")
                return False
            
            self.context.add_cookies(cookies)
            logger.info(f"Cookies 已加载 ({len(cookies)} 条)")
            return True
        except Exception as e:
            logger.warning(f"加载 Cookies 失败: {e}")
            return False
    
    def _is_on_login_page(self) -> bool:
        """检查当前页面是否是登录页（不导航，只检查当前状态）"""
        if not self.page:
            return True
        
        try:
            current_url = self.page.url.lower()
            
            # URL 包含登录相关特征 → 在登录页
            for pattern in self.LOGIN_URL_PATTERNS:
                if pattern in current_url:
                    return True
            
            # 检查页面元素
            try:
                # 检查二维码（登录页特征）
                qr_elements = self.page.locator(
                    'img[src*="qrcode"], [class*="qr"], [class*="login"], .qrcode, #qr'
                ).count()
                
                # 检查"扫码登录"文字
                scan_text = self.page.locator('text=/扫码登录|二维码登录/').count()
                
                if qr_elements > 0 and scan_text > 0:
                    return True
                
            except:
                pass
            
            return False
            
        except Exception:
            return True
    
    def _is_logged_in_quick(self) -> bool:
        """
        快速检查是否已登录（不导航，只看当前页面）
        
        比 check_login_status 更轻量，不会改变页面状态
        """
        if not self.page:
            return False
        
        try:
            # 如果标记为已登录，直接返回
            if self._is_logged_in:
                return True
            
            current_url = self.page.url.lower()
            
            # 在登录页 → 未登录
            for pattern in self.LOGIN_URL_PATTERNS:
                if pattern in current_url:
                    return False
            
            # 在 workbench 页面 → 已登录
            if 'workbench' in current_url and '/login' not in current_url:
                self._is_logged_in = True
                return True
            
            # 检查页面是否有用户相关元素（已登录特征）
            try:
                # "我要续费" 是已登录的特征
                user_indicators = self.page.locator(
                    'text=/我要续费|个人中心|我的|退出|监控中心|选品导航/'
                ).count()
                
                if user_indicators >= 2:
                    self._is_logged_in = True
                    return True
            except:
                pass
            
            return False
            
        except Exception:
            return False
    
    def check_login_status(self) -> Tuple[bool, str]:
        """
        检查登录状态（导航到工作台页面验证）
        
        注意：导航到 WORKBENCH_URL，如果未登录会自动跳转到登录页
        如果已登录则直接显示工作台
        
        Returns:
            (是否已登录, 当前状态描述)
        """
        if not self.page:
            return False, "浏览器未启动"
        
        try:
            # 导航到工作台页面（而非公开首页）
            # 如果已登录 → 显示工作台
            # 如果未登录 → 自动跳转到 /workbench/login
            logger.info(f"导航到工作台: {self.WORKBENCH_URL}")
            
            self.page.goto(self.WORKBENCH_URL, wait_until='domcontentloaded', timeout=30000)
            
            # 等待页面稳定
            time.sleep(3)
            try:
                self.page.wait_for_load_state('networkidle', timeout=8000)
            except:
                pass
            
            self._take_screenshot('check_login')
            
            current_url = self.page.url.lower()
            logger.info(f"当前 URL: {current_url}")
            
            # 检查是否在登录页
            for pattern in self.LOGIN_URL_PATTERNS:
                if pattern in current_url:
                    self._is_logged_in = False
                    return False, f"未登录（URL 包含: {pattern}）"
            
            # 在 workbench 页面 → 已登录
            if 'workbench' in current_url:
                self._is_logged_in = True
                return True, "已登录（在工作台）"
            
            # 在首页但不在登录页 → 检查页面元素
            if self._is_on_login_page():
                self._is_logged_in = False
                return False, "未登录（检测到登录元素）"
            
            self._is_logged_in = True
            return True, "已登录（URL 正常）"
            
        except PlaywrightTimeout:
            return False, "页面加载超时"
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return False, f"检查失败: {e}"
    
    def wait_for_manual_login(self, timeout: int = 180) -> bool:
        """
        等待用户手动登录（扫码）
        
        重要：不会关闭/重启浏览器，不会清除 cookies
        直接在当前浏览器窗口中等待用户扫码登录
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            是否成功登录
        """
        if not self.page:
            logger.error("浏览器未启动")
            return False
        
        logger.info("=" * 60)
        logger.info("请在浏览器窗口中使用微信扫码登录知虾...")
        logger.info(f"超时时间: {timeout} 秒")
        logger.info("=" * 60)
        
        # 导航到工作台页面（会自动跳转到登录页）
        self.page.goto(self.WORKBENCH_URL, wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)
        
        try:
            self.page.wait_for_load_state('networkidle', timeout=5000)
        except:
            pass
        
        self._take_screenshot('login_page')
        logger.info("登录页面已加载，等待扫码...")
        
        start_time = time.time()
        check_interval = 3
        
        while time.time() - start_time < timeout:
            try:
                current_url = self.page.url.lower()
                
                # 检查是否已登录成功
                # 登录成功标志：URL 不再是 login 页面，且包含 workbench
                is_still_login = any(p in current_url for p in self.LOGIN_URL_PATTERNS)
                
                if not is_still_login and 'workbench' in current_url:
                    logger.info("检测到登录成功!")
                    self._is_logged_in = True
                    self._take_screenshot('login_success')
                    self._save_cookies_internal()
                    
                    # 等待页面完全加载
                    time.sleep(2)
                    try:
                        self.page.wait_for_load_state('networkidle', timeout=5000)
                    except:
                        pass
                    
                    return True
                
                # 每 30 秒截图一次
                elapsed = int(time.time() - start_time)
                if elapsed % 30 == 0 and elapsed > 0:
                    self._take_screenshot(f'login_waiting_{elapsed}s')
                    logger.info(f"等待登录... 已等待 {elapsed} 秒")
                
            except Exception as e:
                logger.warning(f"检查登录状态时出错: {e}")
            
            time.sleep(check_interval)
        
        logger.warning("登录超时")
        self._take_screenshot('login_timeout')
        return False
    
    def ensure_login(self, force_visible: bool = False, auto_login_timeout: int = 180) -> Tuple[bool, str]:
        """
        确保已登录（智能登录流程）
        
        v2 改进：
        1. 先尝试无头模式 + cookies
        2. 如果 cookies 无效，切换到可见模式等待手动登录
        3. 不会在登录后关闭浏览器
        4. 登录检测使用工作台页面而非公开首页
        
        Args:
            force_visible: 强制使用可见模式（用于首次登录）
            auto_login_timeout: 手动登录超时时间
            
        Returns:
            (是否成功, 状态描述)
        """
        self._login_attempts += 1
        
        if self._login_attempts > self._max_login_attempts:
            return False, f"登录尝试次数已达上限 ({self._max_login_attempts})，请稍后再试"
        
        # --- 阶段1：尝试无头模式 + cookies ---
        if not force_visible:
            logger.info("阶段1: 尝试无头模式 + Cookies 登录...")
            
            if not self.launch_browser(headless=True):
                return False, "浏览器启动失败"
            
            # 加载 cookies
            self.load_cookies()
            
            # 检查登录状态（导航到工作台）
            is_logged_in, status = self.check_login_status()
            
            if is_logged_in:
                logger.info(f"登录成功: {status}")
                return True, status
            
            logger.info(f"Cookies 无效: {status}")
            
            # 关闭无头浏览器，准备切换到可见模式
            self.close_browser(save_cookies=False)
            time.sleep(1)
        
        # --- 阶段2：可见模式手动登录 ---
        logger.info("阶段2: 启动可见模式，等待手动扫码登录...")
        
        if not self.launch_browser(headless=False):
            return False, "浏览器启动失败"
        
        # 尝试加载 cookies（如果有的话）
        self.load_cookies()
        
        # 先检查一遍（可能 cookies 在可见模式下有效）
        self.page.goto(self.WORKBENCH_URL, wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)
        try:
            self.page.wait_for_load_state('networkidle', timeout=5000)
        except:
            pass
        
        if self._is_logged_in_quick():
            logger.info("Cookies 在可见模式下有效，已登录")
            return True, "已登录（可见模式 + cookies）"
        
        # 等待手动登录
        if not self.wait_for_manual_login(timeout=auto_login_timeout):
            self.close_browser()
            return False, "手动登录超时"
        
        # 登录成功，保持浏览器打开
        logger.info("登录成功，浏览器保持打开状态")
        return True, "登录成功"
    
    # --- 便捷方法 ---
    
    def get_page(self) -> Optional[Page]:
        """获取当前页面对象"""
        return self.page
    
    def get_browser(self) -> Optional[Browser]:
        """获取当前浏览器对象"""
        return self.browser
    
    def get_context(self) -> Optional[BrowserContext]:
        """获取当前上下文对象"""
        return self.context
    
    @property
    def is_logged_in(self) -> bool:
        """是否已登录"""
        return self._is_logged_in or self._is_logged_in_quick()


def test_login_flow():
    """测试登录流程"""
    print("=" * 60)
    print("知虾登录流程测试")
    print("=" * 60)
    
    manager = ZhixiaLoginManager()
    
    # 测试无头模式 + cookies
    print("\n1. 测试无头模式 + Cookies 登录...")
    success, status = manager.ensure_login(auto_login_timeout=10)
    
    if success:
        print(f"   ✓ 成功: {status}")
        # 测试保持登录状态
        print("\n2. 验证登录状态保持...")
        if manager.is_logged_in:
            print("   ✓ 登录状态保持正常")
        else:
            print("   ✗ 登录状态丢失")
        manager.close_browser()
        return True
    
    print(f"   ✗ 未登录: {status}")
    
    # 需要手动登录
    print("\n2. 需要手动登录...")
    print("   请在浏览器窗口中扫码登录...")
    
    # 注意：不要再调用 ensure_login，直接调用 wait_for_manual_login
    # 因为 ensure_login 已经关闭了无头浏览器
    
    success, status = manager.ensure_login(force_visible=True, auto_login_timeout=180)
    
    if success:
        print(f"   ✓ 登录成功: {status}")
        print("   Cookies 已保存，下次可直接使用")
        manager.close_browser()
        return True
    
    print(f"   ✗ 登录失败: {status}")
    manager.close_browser()
    return False


if __name__ == '__main__':
    success = test_login_flow()
    sys.exit(0 if success else 1)