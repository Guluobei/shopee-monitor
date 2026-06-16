#!/usr/bin/env python3
"""
优化版Cookie管理器
核心特性：
1. Cookie新鲜度检测 - 30分钟内不重复登录
2. 快速验证 - 不启动完整浏览器
3. 内存缓存 - session级别复用
4. 持久化缓存 - 记住成功过的登录
"""
import os
import time
import json
import logging
import hashlib
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class OptimizedCookieManager:
    """
    优化版Cookie管理器
    
    优化策略：
    - Cookie新鲜度阈值：30分钟（新鲜）、2小时（过期）
    - 快速验证：启动轻量级浏览器验证Cookie
    - 内存缓存：同一进程内不重复加载
    - 持久化：记住验证结果，加速下次启动
    """
    
    # Cookie新鲜度阈值（秒）
    COOKIE_FRESH_THRESHOLD = 30 * 60      # 30分钟内认为新鲜
    COOKIE_WARN_THRESHOLD = 60 * 60       # 1小时以上警告
    COOKIE_EXPIRED_THRESHOLD = 2 * 60 * 60  # 2小时以上认为过期
    
    # 缓存文件
    VALIDATION_CACHE_FILE = ".cookie_validation_cache.json"
    SESSION_CACHE_FILE = ".session_cache.json"
    
    def __init__(self, cookie_file: str, cache_dir: str = None):
        """
        初始化Cookie管理器
        
        Args:
            cookie_file: Cookie文件路径
            cache_dir: 缓存目录，默认使用cookie_file同级目录
        """
        self.cookie_file = cookie_file
        
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(cookie_file).parent
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 验证缓存
        self.validation_cache_file = self.cache_dir / self.VALIDATION_CACHE_FILE
        self.validation_cache: Dict[str, Any] = self._load_validation_cache()
        
        # Session缓存（内存）
        self._session_cache: Dict[str, Any] = {
            'cookies': None,
            'loaded_time': 0,
            'validated': False,
        }
    
    # ==================== 缓存管理 ====================
    
    def _load_validation_cache(self) -> Dict:
        """加载验证缓存"""
        if self.validation_cache_file.exists():
            try:
                with open(self.validation_cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载验证缓存失败: {e}")
        return {}
    
    def _save_validation_cache(self):
        """保存验证缓存"""
        try:
            with open(self.validation_cache_file, 'w') as f:
                json.dump(self.validation_cache, f, indent=2)
        except Exception as e:
            logger.warning(f"保存验证缓存失败: {e}")
    
    # ==================== 核心功能 ====================
    
    def get_cookie_age(self) -> Tuple[float, str]:
        """
        获取Cookie文件年龄
        
        Returns:
            (年龄秒数, 状态描述)
        """
        if not os.path.exists(self.cookie_file):
            return -1, "文件不存在"
        
        mtime = os.path.getmtime(self.cookie_file)
        age = time.time() - mtime
        
        if age < self.COOKIE_FRESH_THRESHOLD:
            return age, "新鲜"
        elif age < self.COOKIE_WARN_THRESHOLD:
            return age, "可用"
        elif age < self.COOKIE_EXPIRED_THRESHOLD:
            return age, "即将过期"
        else:
            return age, "已过期"
    
    def is_cookie_fresh(self) -> bool:
        """
        快速检查Cookie是否新鲜
        
        Returns:
            True 如果Cookie在30分钟内创建/更新过
        """
        age, status = self.get_cookie_age()
        if age < 0:
            return False
        return age < self.COOKIE_FRESH_THRESHOLD
    
    def load_cookies(self) -> Optional[list]:
        """
        加载Cookie（带缓存）
        
        Returns:
            Cookie列表或None
        """
        # 检查session缓存
        if self._session_cache['cookies'] is not None:
            if time.time() - self._session_cache['loaded_time'] < 300:  # 5分钟内复用
                logger.info("使用session缓存的cookies")
                return self._session_cache['cookies']
        
        # 加载文件
        if not os.path.exists(self.cookie_file):
            logger.warning("Cookie文件不存在")
            return None
        
        try:
            with open(self.cookie_file, 'r') as f:
                cookies = json.load(f)
            
            if not cookies:
                logger.warning("Cookie文件为空")
                return None
            
            # 更新session缓存
            self._session_cache['cookies'] = cookies
            self._session_cache['loaded_time'] = time.time()
            
            age, status = self.get_cookie_age()
            logger.info(f"已加载 {len(cookies)} 个cookies, 状态: {status} ({age/60:.1f}分钟)")
            
            return cookies
            
        except Exception as e:
            logger.error(f"加载Cookie失败: {e}")
            return None
    
    def save_cookies(self, cookies: list) -> bool:
        """
        保存Cookie
        
        Args:
            cookies: Cookie列表
            
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.cookie_file) or '.', exist_ok=True)
            
            with open(self.cookie_file, 'w') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            
            # 更新session缓存
            self._session_cache['cookies'] = cookies
            self._session_cache['loaded_time'] = time.time()
            
            logger.info(f"已保存 {len(cookies)} 个cookies")
            return True
            
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
            return False
    
    def validate_with_cache(self, workbench_url: str, check_func) -> Tuple[bool, str]:
        """
        带缓存的Cookie验证
        
        Args:
            workbench_url: 工作台URL
            check_func: 验证函数，接收cookies和url，返回(bool, str)
            
        Returns:
            (是否有效, 原因)
        """
        cookies = self.load_cookies()
        if not cookies:
            return False, "无Cookie可验证"
        
        # 检查验证缓存
        cache_key = self._get_cache_key(cookies)
        cached_result = self.validation_cache.get(cache_key)
        
        if cached_result:
            cached_time = cached_result.get('time', 0)
            cached_valid = cached_result.get('valid', False)
            cache_age = time.time() - cached_time
            
            # 缓存5分钟内，认为有效
            if cache_age < 300 and cached_valid:
                logger.info(f"使用验证缓存（{cache_age:.0f}秒前）: 有效")
                return True, "缓存有效"
            
            # 缓存超过30分钟，重新验证
            if cache_age > 1800:
                logger.info(f"验证缓存过期（{cache_age/60:.0f}分钟前），重新验证")
            else:
                logger.info(f"缓存无效（{cache_age:.0f}秒前），重新验证")
        
        # 执行验证
        is_valid, reason = check_func(cookies, workbench_url)
        
        # 更新验证缓存
        self.validation_cache[cache_key] = {
            'valid': is_valid,
            'time': time.time(),
            'reason': reason,
        }
        self._save_validation_cache()
        
        return is_valid, reason
    
    def _get_cache_key(self, cookies: list) -> str:
        """生成缓存键"""
        # 使用cookie数量和部分内容生成hash
        content = f"{len(cookies)}_{cookies[0] if cookies else ''}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def invalidate_cache(self):
        """使缓存失效（强制重新验证）"""
        self.validation_cache = {}
        self._save_validation_cache()
        self._session_cache = {
            'cookies': None,
            'loaded_time': 0,
            'validated': False,
        }
        logger.info("Cookie缓存已清除")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取Cookie状态
        
        Returns:
            状态字典
        """
        age, status = self.get_cookie_age()
        
        return {
            'cookie_file': self.cookie_file,
            'exists': os.path.exists(self.cookie_file),
            'age_seconds': age,
            'age_minutes': age / 60 if age > 0 else 0,
            'status': status,
            'is_fresh': age >= 0 and age < self.COOKIE_FRESH_THRESHOLD,
            'cookie_count': len(self.load_cookies()) if os.path.exists(self.cookie_file) else 0,
        }


class QuickCookieValidator:
    """
    快速Cookie验证器
    
    启动轻量级浏览器验证Cookie是否有效
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
    
    def validate(self, cookies: list, workbench_url: str, timeout: int = 10) -> Tuple[bool, str]:
        """
        验证Cookie是否有效
        
        Args:
            cookies: Cookie列表
            workbench_url: 工作台URL
            timeout: 超时时间（秒）
            
        Returns:
            (是否有效, 原因)
        """
        try:
            from playwright.sync_api import sync_playwright
            
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=self.headless)
            context = browser.new_context()
            
            # 设置Cookie
            context.add_cookies(cookies)
            
            # 创建页面
            page = context.new_page()
            
            # 访问并快速检测
            try:
                page.goto(workbench_url, wait_until='domcontentloaded', timeout=timeout * 1000)
                time.sleep(1)
                
                # 检测URL
                url = page.url.lower()
                login_indicators = ['/login', 'signin', 'passport', 'auth']
                
                if any(ind in url for ind in login_indicators):
                    browser.close()
                    playwright.stop()
                    return False, "Cookie已失效（被重定向到登录页）"
                
                # 检查页面内容
                try:
                    page_text = page.inner_text('body', timeout=2000)
                    if '请登录' in page_text[:200] or '登录' in page_text[:100]:
                        browser.close()
                        playwright.stop()
                        return False, "Cookie已失效（页面显示需要登录）"
                except:
                    pass
                
                browser.close()
                playwright.stop()
                return True, "Cookie有效"
                
            except Exception as e:
                browser.close()
                playwright.stop()
                return False, f"验证失败: {str(e)[:50]}"
                
        except ImportError:
            logger.warning("Playwright未安装，跳过验证")
            return True, "跳过验证（Playwright未安装）"
        except Exception as e:
            logger.error(f"Cookie验证异常: {e}")
            return False, f"验证异常: {str(e)[:50]}"


def quick_validate_cookies(cookie_file: str, workbench_url: str) -> Tuple[bool, str]:
    """
    快速验证Cookie（便捷函数）
    
    Args:
        cookie_file: Cookie文件路径
        workbench_url: 工作台URL
        
    Returns:
        (是否有效, 原因)
    """
    manager = OptimizedCookieManager(cookie_file)
    validator = QuickCookieValidator(headless=True)
    
    return manager.validate_with_cache(workbench_url, validator.validate)
