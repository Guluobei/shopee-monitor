#!/usr/bin/env python3
"""
知虾登录模块 v3
基于 Playwright 的智能登录管理
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ZhixiaLoginManager:
    """知虾登录管理器 v3"""
    
    BASE_URL = 'https://shopee.menglar.com'
    WORKBENCH_URL = 'https://shopee.menglar.com/workbench/home'
    
    LOGIN_PATTERNS = ['/login', 'signin', 'passport', 'auth']
    
    def __init__(self, config: Dict = None, cookie_file: str = None, screenshot_dir: str = None):
        self.config = config or {
            'zhixia': {
                'base_url': self.BASE_URL,
                'login_url': self.WORKBENCH_URL
            }
        }
        
        self.cookie_file = cookie_file or os.path.join(
            os.path.dirname(__file__), '..', 'data', 'cookies.json'
        )
        os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
        
        self.screenshot_dir = screenshot_dir or os.path.join(
            os.path.dirname(__file__), '..', 'data', 'screenshots'
        )
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        self._is_logged_in = False
        self._login_attempts = 0
        self._max_attempts = 2
    
    def _take_screenshot(self, name: str) -> str:
        if not self.page:
            return ""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}.png"
        filepath = os.path.join(self.screenshot_dir, filename)
        
        try:
            self.page.screenshot(path=filepath, full_page=True)
            logger.info(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")
            return ""
    
    def launch_browser(self, headless: bool = True) -> bool:
        """启动浏览器"""
        # 清理旧实例
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
        
        logger.info("Starting browser...")
        
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                ]
            )
            
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                accept_downloads=True,
            )
            
            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
            """)
            
            self.page = self.context.new_page()
            self._is_logged_in = False
            logger.info("Browser started")
            return True
            
        except Exception as e:
            logger.error(f"Browser start failed: {e}")
            return False
    
    def close_browser(self, save_cookies: bool = True) -> None:
        """关闭浏览器"""
        try:
            if save_cookies and self.context:
                try:
                    self._save_cookies()
                except Exception as e:
                    logger.warning(f"Save cookies error: {e}")
            
            if self.browser:
                try:
                    self.browser.close()
                except Exception as e:
                    logger.warning(f"Close browser error: {e}")
            
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception as e:
                    logger.warning(f"Stop playwright error: {e}")
            
            self.browser = None
            self.context = None
            self.page = None
            self.playwright = None
            self._is_logged_in = False
            
            logger.info("Browser closed")
        except Exception as e:
            logger.warning(f"Close error: {e}")
    
    def _save_cookies(self) -> bool:
        """保存 cookies"""
        if not self.context:
            return False
        
        try:
            cookies = self.context.cookies()
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"Cookies saved: {self.cookie_file}")
            return True
        except Exception as e:
            logger.warning(f"Save cookies failed: {e}")
            return False
    
    def save_cookies(self) -> bool:
        return self._save_cookies()
    
    def load_cookies(self) -> bool:
        """加载 cookies"""
        if not self.context or not os.path.exists(self.cookie_file):
            return False
        
        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            if not cookies:
                logger.info("Cookies file empty")
                return False
            
            self.context.add_cookies(cookies)
            logger.info(f"Cookies loaded: {len(cookies)}")
            return True
        except Exception as e:
            logger.warning(f"Load cookies failed: {e}")
            return False
    
    def _is_on_login_page(self) -> bool:
        """检查是否在登录页"""
        if not self.page:
            return True
        
        try:
            current_url = self.page.url.lower()
            
            for pattern in self.LOGIN_PATTERNS:
                if pattern in current_url:
                    return True
            
            # 检查页面元素
            try:
                qr_count = self.page.locator(
                    'img[src*="qrcode"], [class*="qr"], .qrcode'
                ).count()
                
                scan_text = self.page.locator('text=/扫码登录|二维码登录/').count()
                
                if qr_count > 0 and scan_text > 0:
                    return True
            except:
                pass
            
            return False
            
        except Exception:
            return True
    
    def _check_logged_in_quick(self) -> bool:
        """快速检查登录状态"""
        if not self.page:
            return False
        
        try:
            if self._is_logged_in:
                return True
            
            current_url = self.page.url.lower()
            
            for pattern in self.LOGIN_PATTERNS:
                if pattern in current_url:
                    return False
            
            if 'workbench' in current_url and '/login' not in current_url:
                self._is_logged_in = True
                return True
            
            # 检查用户元素
            try:
                user_count = self.page.locator(
                    'text=/我要续费|个人中心|监控中心|选品导航/'
                ).count()
                
                if user_count >= 2:
                    self._is_logged_in = True
                    return True
            except:
                pass
            
            return False
            
        except Exception:
            return False
    
    def check_login_status(self) -> Tuple[bool, str]:
        """检查登录状态"""
        if not self.page:
            return False, "Browser not started"
        
        try:
            logger.info(f"Navigating to: {self.WORKBENCH_URL}")
            
            self.page.goto(self.WORKBENCH_URL, wait_until='domcontentloaded', timeout=30000)
            
            time.sleep(3)
            try:
                self.page.wait_for_load_state('networkidle', timeout=8000)
            except:
                pass
            
            self._take_screenshot('check_login')
            
            current_url = self.page.url.lower()
            logger.info(f"Current URL: {current_url}")
            
            for pattern in self.LOGIN_PATTERNS:
                if pattern in current_url:
                    self._is_logged_in = False
                    return False, f"Not logged in (URL: {pattern})"
            
            if 'workbench' in current_url:
                self._is_logged_in = True
                return True, "Logged in (workbench)"
            
            if self._is_on_login_page():
                self._is_logged_in = False
                return False, "Not logged in (login elements)"
            
            self._is_logged_in = True
            return True, "Logged in"
            
        except PlaywrightTimeout:
            return False, "Page timeout"
        except Exception as e:
            logger.error(f"Check login failed: {e}")
            return False, f"Error: {e}"
    
    def wait_for_manual_login(self, timeout: int = 180) -> bool:
        """等待手动登录"""
        if not self.page:
            logger.error("Browser not started")
            return False
        
        logger.info("=" * 60)
        logger.info("Please scan QR code in browser window...")
        logger.info(f"Timeout: {timeout} seconds")
        logger.info("=" * 60)
        
        self.page.goto(self.WORKBENCH_URL, wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)
        
        try:
            self.page.wait_for_load_state('networkidle', timeout=5000)
        except:
            pass
        
        self._take_screenshot('login_page')
        logger.info("Login page loaded, waiting for scan...")
        
        start_time = time.time()
        check_interval = 3
        
        while time.time() - start_time < timeout:
            try:
                current_url = self.page.url.lower()
                
                is_login_page = any(p in current_url for p in self.LOGIN_PATTERNS)
                
                if not is_login_page and 'workbench' in current_url:
                    logger.info("Login detected!")
                    self._is_logged_in = True
                    self._take_screenshot('login_success')
                    self._save_cookies()
                    
                    time.sleep(2)
                    try:
                        self.page.wait_for_load_state('networkidle', timeout=5000)
                    except:
                        pass
                    
                    return True
                
                elapsed = int(time.time() - start_time)
                if elapsed % 30 == 0 and elapsed > 0:
                    self._take_screenshot(f'waiting_{elapsed}s')
                    logger.info(f"Waiting... {elapsed}s elapsed")
                
            except Exception as e:
                logger.warning(f"Check error: {e}")
            
            time.sleep(check_interval)
        
        logger.warning("Login timeout")
        self._take_screenshot('login_timeout')
        return False
    
    def ensure_login(self, force_visible: bool = False, auto_login_timeout: int = 180) -> Tuple[bool, str]:
        """确保已登录"""
        self._login_attempts += 1
        
        if self._login_attempts > self._max_attempts:
            return False, f"Max attempts reached ({self._max_attempts})"
        
        # 阶段1: 无头模式 + cookies
        if not force_visible:
            logger.info("Phase 1: Headless + Cookies...")
            
            if not self.launch_browser(headless=True):
                return False, "Browser start failed"
            
            self.load_cookies()
            
            is_logged_in, status = self.check_login_status()
            
            if is_logged_in:
                logger.info(f"Login success: {status}")
                return True, status
            
            logger.info(f"Cookies invalid: {status}")
            
            self.close_browser(save_cookies=False)
            time.sleep(1)
        
        # 阶段2: 可见模式手动登录
        logger.info("Phase 2: Visible mode, manual login...")
        
        if not self.launch_browser(headless=False):
            return False, "Browser start failed"
        
        self.load_cookies()
        
        self.page.goto(self.WORKBENCH_URL, wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)
        try:
            self.page.wait_for_load_state('networkidle', timeout=5000)
        except:
            pass
        
        if self._check_logged_in_quick():
            logger.info("Cookies valid in visible mode")
            return True, "Logged in (visible + cookies)"
        
        if not self.wait_for_manual_login(timeout=auto_login_timeout):
            self.close_browser()
            return False, "Manual login timeout"
        
        logger.info("Login success, browser kept open")
        return True, "Login success"
    
    def get_page(self) -> Optional[Page]:
        return self.page
    
    def get_browser(self) -> Optional[Browser]:
        return self.browser
    
    def get_context(self) -> Optional[BrowserContext]:
        return self.context
    
    @property
    def is_logged_in(self) -> bool:
        return self._is_logged_in or self._check_logged_in_quick()


def test_login():
    """测试登录流程"""
    print("=" * 60)
    print("Login Test")
    print("=" * 60)
    
    manager = ZhixiaLoginManager()
    
    print("\n1. Testing headless + cookies...")
    success, status = manager.ensure_login(auto_login_timeout=10)
    
    if success:
        print(f"   OK: {status}")
        print("\n2. Verifying login state...")
        if manager.is_logged_in:
            print("   OK: Login state maintained")
        else:
            print("   FAIL: Login state lost")
        manager.close_browser()
        return True
    
    print(f"   FAIL: {status}")
    
    print("\n2. Manual login required...")
    print("   Please scan QR code in browser...")
    
    success, status = manager.ensure_login(force_visible=True, auto_login_timeout=180)
    
    if success:
        print(f"   OK: {status}")
        print("   Cookies saved")
        manager.close_browser()
        return True
    
    print(f"   FAIL: {status}")
    manager.close_browser()
    return False


if __name__ == '__main__':
    success = test_login()
    sys.exit(0 if success else 1)