#!/usr/bin/env python3
"""
优化版登录管理器
核心特性：
1. 快速失败 - 30分钟内不重复登录
2. 智能Cookie验证 - 不启动完整浏览器
3. Session缓存 - 同一进程复用
4. 两阶段登录 - headless快速检测 + 可视化手动登录
"""
import os
import sys
import time
import json
import logging
import tempfile
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

from optimized_cookie_manager import OptimizedCookieManager, QuickCookieValidator
from smart_wait import SmartWait

logger = logging.getLogger(__name__)


class LoginState:
    """登录状态枚举"""
    UNKNOWN = "unknown"
    COOKIE_VALID = "cookie_valid"
    COOKIE_EXPIRED = "cookie_expired"
    NEED_MANUAL_LOGIN = "need_manual_login"
    LOGGING_IN = "logging_in"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"


class OptimizedLoginManager:
    """
    优化版登录管理器
    
    优化策略：
    1. Cookie新鲜度检测：30分钟内不重新验证
    2. 快速验证：轻量级浏览器，10秒超时
    3. Session缓存：同一进程内不重复启动浏览器
    4. 两阶段登录：headless检测失败后，再启动可视化
    """
    
    # 常量
    WORKBENCH_URL = 'https://shopee.menglar.com/workbench/home'
    LOGIN_PATTERNS = ['/login', 'signin', 'passport', 'auth']
    
    # 超时设置
    QUICK_VALIDATE_TIMEOUT = 10      # 快速验证超时（秒）
    MANUAL_LOGIN_TIMEOUT = 120       # 手动登录超时（秒）
    PAGE_LOAD_TIMEOUT = 30          # 页面加载超时（秒）
    
    # Cookie阈值
    COOKIE_FRESH_THRESHOLD = 30 * 60     # 30分钟内认为新鲜
    SESSION_CACHE_DURATION = 30 * 60      # Session缓存30分钟
    
    def __init__(
        self,
        cookie_file: str = None,
        screenshot_dir: str = None,
        cache_dir: str = None
    ):
        """
        初始化登录管理器
        
        Args:
            cookie_file: Cookie文件路径
            screenshot_dir: 截图保存目录
            cache_dir: 缓存目录
        """
        # 设置默认路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if cookie_file is None:
            cookie_file = os.path.join(base_dir, 'data', 'cookies.json')
        if screenshot_dir is None:
            screenshot_dir = os.path.join(base_dir, 'data', 'login_screenshots')
        if cache_dir is None:
            cache_dir = os.path.join(base_dir, 'data', 'cache')
        
        # 确保目录存在
        for d in [cookie_file, screenshot_dir, cache_dir]:
            parent = os.path.dirname(d)
            if parent:
                os.makedirs(parent, exist_ok=True)
        
        self.cookie_file = cookie_file
        self.screenshot_dir = screenshot_dir
        self.cache_dir = cache_dir
        
        # Cookie管理器
        self.cookie_manager = OptimizedCookieManager(
            cookie_file=cookie_file,
            cache_dir=cache_dir
        )
        
        # Playwright对象
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # 状态
        self._state = LoginState.UNKNOWN
        self._last_login_time = 0
        self._login_attempts = 0
        self._max_attempts = 3
        
        # Session缓存（类级别，跨实例共享）
        if not hasattr(OptimizedLoginManager, '_global_session'):
            OptimizedLoginManager._global_session = {
                'active': False,
                'login_time': 0,
                'browser': None,
                'context': None,
                'page': None,
            }
        self._session = OptimizedLoginManager._global_session
    
    # ==================== 状态管理 ====================
    
    def _set_state(self, state: str, message: str = ""):
        """设置状态"""
        self._state = state
        logger.info(f"[登录状态] {state} {message}")
    
    def get_state(self) -> str:
        """获取当前状态"""
        return self._state
    
    # ==================== Session管理 ====================
    
    def _is_session_valid(self) -> bool:
        """检查Session缓存是否有效"""
        if not self._session['active']:
            return False
        
        if time.time() - self._session['login_time'] > self.SESSION_CACHE_DURATION:
            self._session['active'] = False
            return False
        
        return True
    
    def _save_to_session(self):
        """保存到Session缓存"""
        self._session['active'] = True
        self._session['login_time'] = time.time()
        self._session['browser'] = self.browser
        self._session['context'] = self.context
        self._session['page'] = self.page
        self._last_login_time = time.time()
    
    def _restore_from_session(self) -> bool:
        """从Session缓存恢复"""
        if not self._is_session_valid():
            return False
        
        self.browser = self._session.get('browser')
        self.context = self._session.get('context')
        self.page = self._session.get('page')
        
        # 验证页面是否还可用
        if self.page:
            try:
                url = self.page.url
                if any(p in url.lower() for p in self.LOGIN_PATTERNS):
                    # Session已失效
                    self._session['active'] = False
                    return False
                return True
            except:
                self._session['active'] = False
                return False
        
        return False
    
    # ==================== 浏览器管理 ====================
    
    def _launch_browser(self, headless: bool = False) -> bool:
        """启动浏览器"""
        try:
            from playwright.sync_api import sync_playwright
            
            # 清理旧实例
            self._cleanup_browser()
            
            logger.info(f"启动浏览器 (headless={headless})...")
            
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            
            self.context = self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                accept_downloads=True,
            )
            
            # 隐藏自动化特征
            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                window.chrome = { runtime: {} };
            """)
            
            self.page = self.context.new_page()
            
            logger.info("浏览器启动成功")
            return True
            
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            return False
    
    def _cleanup_browser(self):
        """清理浏览器"""
        try:
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
        except Exception:
            pass
        
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
    
    def close_browser(self, save_cookies: bool = True):
        """关闭浏览器"""
        if save_cookies:
            self._save_cookies()
        self._cleanup_browser()
        self._session['active'] = False
    
    # ==================== Cookie管理 ====================
    
    def _save_cookies(self):
        """保存Cookie"""
        if self.context:
            try:
                cookies = self.context.cookies()
                self.cookie_manager.save_cookies(cookies)
                logger.info(f"Cookie已保存 ({len(cookies)}个)")
            except Exception as e:
                logger.warning(f"Cookie保存失败: {e}")
    
    def _load_cookies(self):
        """加载Cookie"""
        return self.cookie_manager.load_cookies()
    
    # ==================== 登录检测 ====================
    
    def _is_on_login_page(self) -> bool:
        """检查是否在登录页"""
        if not self.page:
            return True
        
        try:
            url = self.page.url.lower()
            for pattern in self.LOGIN_PATTERNS:
                if pattern in url:
                    return True
            return False
        except:
            return True
    
    def _take_screenshot(self, name: str) -> str:
        """截图"""
        if not self.page:
            return ""
        
        os.makedirs(self.screenshot_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}.png"
        filepath = os.path.join(self.screenshot_dir, filename)
        
        try:
            self.page.screenshot(path=filepath, full_page=True)
            logger.info(f"截图已保存: {filepath}")
            return filepath
        except Exception as e:
            logger.warning(f"截图失败: {e}")
            return ""
    
    # ==================== 核心登录流程 ====================
    
    def ensure_login(self, force: bool = False) -> Tuple[bool, str]:
        """
        确保已登录 - 优化版
        
        流程：
        1. 检查Session缓存（同一进程）
        2. 检查Cookie新鲜度
        3. 快速验证Cookie（headless）
        4. 失败则启动可视化手动登录
        
        Args:
            force: 是否强制重新登录
            
        Returns:
            (是否成功, 原因)
        """
        self._login_attempts += 1
        
        if self._login_attempts > self._max_attempts:
            return False, f"超过最大尝试次数({self._max_attempts})"
        
        # 1. 检查Session缓存
        if not force and self._is_session_valid():
            if self._restore_from_session():
                self._set_state(LoginState.LOGIN_SUCCESS, "session缓存有效")
                return True, "session缓存有效"
        
        # 2. 检查Cookie新鲜度
        if not force:
            age, status = self.cookie_manager.get_cookie_age()
            if age >= 0 and age < self.COOKIE_FRESH_THRESHOLD:
                logger.info(f"Cookie新鲜 ({status}), 尝试快速验证...")
        
        # 3. 尝试快速验证
        if not force:
            success, reason = self._quick_validate()
            if success:
                self._set_state(LoginState.COOKIE_VALID, reason)
                
                # 快速验证成功后，需要启动一个可用的浏览器
                if not self._launch_browser(headless=True):
                    return False, "浏览器启动失败"
                
                # 加载Cookie
                self._load_cookies()
                
                # 验证页面可用
                try:
                    self.page.goto(self.WORKBENCH_URL, wait_until='domcontentloaded', timeout=15*1000)
                    time.sleep(2)
                    
                    if not self._is_on_login_page():
                        self._save_to_session()
                        return True, "快速验证成功"
                except:
                    pass
        
        # 4. 可视化手动登录
        return self._manual_login()
    
    def _quick_validate(self) -> Tuple[bool, str]:
        """
        快速验证Cookie
        
        策略：
        1. 使用轻量级headless浏览器
        2. 10秒超时
        3. 不加载Cookie文件，只检测是否存在
        """
        # 检查Cookie文件
        if not os.path.exists(self.cookie_file):
            return False, "Cookie文件不存在"
        
        # 快速检测Cookie年龄
        age, status = self.cookie_manager.get_cookie_age()
        if age < 0:
            return False, "Cookie文件不存在"
        
        if age > 2 * 60 * 60:  # 2小时以上
            return False, f"Cookie过期 ({status})"
        
        # 使用QuickCookieValidator验证
        validator = QuickCookieValidator(headless=True)
        cookies = self._load_cookies()
        
        if not cookies:
            return False, "Cookie为空"
        
        return validator.validate(cookies, self.WORKBENCH_URL, timeout=self.QUICK_VALIDATE_TIMEOUT)
    
    def _manual_login(self) -> Tuple[bool, str]:
        """
        手动登录流程
        
        启动可视化浏览器，等待用户扫码
        """
        self._set_state(LoginState.NEED_MANUAL_LOGIN)
        
        # 启动可视化浏览器
        if not self._launch_browser(headless=False):
            return False, "浏览器启动失败"
        
        # 加载Cookie（可能还有效）
        cookies = self._load_cookies()
        if cookies:
            try:
                self.context.add_cookies(cookies)
            except Exception as e:
                logger.warning(f"加载Cookie失败: {e}")
        
        # 访问登录页
        try:
            self.page.goto(self.WORKBENCH_URL, wait_until='domcontentloaded', timeout=self.PAGE_LOAD_TIMEOUT*1000)
            time.sleep(2)
        except Exception as e:
            logger.warning(f"页面加载失败: {e}")
        
        # 检查是否已登录
        if not self._is_on_login_page():
            self._set_state(LoginState.LOGIN_SUCCESS, "Cookie仍然有效")
            self._save_to_session()
            self._save_cookies()
            return True, "Cookie仍然有效"
        
        # 等待手动登录
        self._set_state(LoginState.LOGGING_IN)
        logger.info("=" * 60)
        logger.info("请在浏览器中扫码登录知虾...")
        logger.info(f"超时时间: {self.MANUAL_LOGIN_TIMEOUT}秒")
        logger.info("=" * 60)
        
        self._take_screenshot('login_page')
        
        success = self._wait_for_login()
        
        if success:
            self._set_state(LoginState.LOGIN_SUCCESS)
            self._save_cookies()
            self._save_to_session()
            self._take_screenshot('login_success')
            return True, "登录成功"
        else:
            self._set_state(LoginState.LOGIN_FAILED)
            self._take_screenshot('login_failed')
            return False, "登录超时"
    
    def _wait_for_login(self) -> bool:
        """
        等待登录完成
        
        轮询检测URL变化
        """
        start_time = time.time()
        check_interval = 2
        last_screenshot = 0
        
        while time.time() - start_time < self.MANUAL_LOGIN_TIMEOUT:
            # 检查URL
            if not self._is_on_login_page():
                logger.info("检测到登录成功!")
                time.sleep(1)  # 等待页面稳定
                return True
            
            # 定期截图（每30秒）
            elapsed = time.time() - start_time
            if elapsed - last_screenshot > 30:
                self._take_screenshot(f'waiting_{int(elapsed)}s')
                last_screenshot = elapsed
                logger.info(f"等待中... {int(elapsed)}秒")
            
            time.sleep(check_interval)
        
        return False
    
    # ==================== 便捷方法 ====================
    
    def get_page(self):
        """获取当前页面"""
        if not self.page and self._is_session_valid():
            self._restore_from_session()
        return self.page
    
    def get_browser(self):
        """获取浏览器对象"""
        return self.browser
    
    def get_context(self):
        """获取浏览器上下文"""
        return self.context
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        page = self.get_page()
        if not page:
            return False
        
        try:
            if self._is_on_login_page():
                return False
            return True
        except:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取登录状态详情"""
        cookie_status = self.cookie_manager.get_status()
        session_valid = self._is_session_valid()
        
        return {
            'state': self._state,
            'session_valid': session_valid,
            'session_age': int(time.time() - self._session['login_time']) if session_valid else None,
            'login_attempts': self._login_attempts,
            'cookie_status': cookie_status,
        }


# 需要datetime
from datetime import datetime
