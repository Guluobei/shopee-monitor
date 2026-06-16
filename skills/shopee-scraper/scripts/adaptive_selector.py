#!/usr/bin/env python3
"""
自适应选择器模块
核心特性：
1. 多选择器备选 - 一个不行换下一个
2. 选择器缓存 - 记住成功的，快速复用
3. 降级策略 - 文本搜索兜底
4. 失败记录 - 避免重复尝试已知失败的选择器
"""
import os
import json
import time
import logging
from typing import List, Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SelectorResult:
    """选择器执行结果"""
    success: bool
    selector: str
    reason: str = ""
    duration_ms: float = 0


@dataclass
class SelectorCache:
    """选择器缓存"""
    successful: Dict[str, str] = field(default_factory=dict)  # strategy_name -> selector
    failed: Dict[str, List[str]] = field(default_factory=dict)  # strategy_name -> [failed_selectors]
    attempt_counts: Dict[str, int] = field(default_factory=dict)  # strategy_name -> count
    success_counts: Dict[str, int] = field(default_factory=dict)  # strategy_name -> count
    
    def to_dict(self) -> dict:
        return {
            'successful': self.successful,
            'failed': self.failed,
            'attempt_counts': self.attempt_counts,
            'success_counts': self.success_counts,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SelectorCache':
        return cls(
            successful=data.get('successful', {}),
            failed=data.get('failed', {}),
            attempt_counts=data.get('attempt_counts', {}),
            success_counts=data.get('success_counts', {}),
        )


class AdaptiveSelector:
    """
    自适应选择器
    
    核心策略：
    1. 优先级：缓存的成功选择器 > 备选列表 > 降级策略
    2. 学习：记住成功的选择器，避免重复尝试失败的
    3. 降级：文本搜索兜底，确保不会完全失败
    """
    
    def __init__(self, page, cache_dir: str = None, cache_prefix: str = "selector"):
        """
        初始化自适应选择器
        
        Args:
            page: Playwright Page对象
            cache_dir: 缓存目录
            cache_prefix: 缓存文件前缀
        """
        self.page = page
        self.cache_dir = Path(cache_dir) if cache_dir else Path('.')
        self.cache_prefix = cache_prefix
        self.cache_file = self.cache_dir / f"{cache_prefix}_cache.json"
        
        # 选择器缓存
        self.cache = self._load_cache()
        
        # 历史记录
        self.history: List[SelectorResult] = []
    
    def _load_cache(self) -> SelectorCache:
        """加载选择器缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return SelectorCache.from_dict(json.load(f))
            except Exception as e:
                logger.warning(f"加载选择器缓存失败: {e}")
        return SelectorCache()
    
    def _save_cache(self):
        """保存选择器缓存"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"保存选择器缓存失败: {e}")
    
    def _record_success(self, strategy_name: str, selector: str):
        """记录成功"""
        self.cache.successful[strategy_name] = selector
        self.cache.success_counts[strategy_name] = self.cache.success_counts.get(strategy_name, 0) + 1
        self._save_cache()
        logger.info(f"✓ [{strategy_name}] 选择器成功: {selector}")
    
    def _record_failure(self, strategy_name: str, selector: str):
        """记录失败"""
        if strategy_name not in self.cache.failed:
            self.cache.failed[strategy_name] = []
        if selector not in self.cache.failed[strategy_name]:
            self.cache.failed[strategy_name].append(selector)
        self.cache.attempt_counts[strategy_name] = self.cache.attempt_counts.get(strategy_name, 0) + 1
        self._save_cache()
        logger.warning(f"✗ [{strategy_name}] 选择器失败: {selector}")
    
    def _is_failed_before(self, strategy_name: str, selector: str) -> bool:
        """检查选择器之前是否失败过"""
        return selector in self.cache.failed.get(strategy_name, [])
    
    # ==================== 核心方法 ====================
    
    def find(
        self,
        strategy_name: str,
        *selectors: str,
        timeout: int = 5000,
        text_filter: str = None
    ) -> Optional[str]:
        """
        智能查找元素
        
        Args:
            strategy_name: 策略名称（用于缓存）
            *selectors: 备选选择器列表
            timeout: 超时时间（毫秒）
            text_filter: 文本过滤器（可选）
            
        Returns:
            成功的选择器或None
        """
        # 过滤掉之前失败过的选择器
        candidates = [s for s in selectors if not self._is_failed_before(strategy_name, s)]
        
        if not candidates and selectors:
            # 如果所有都失败过，降级到尝试所有
            candidates = list(selectors)
            logger.info(f"[{strategy_name}] 所有备选选择器都曾失败过，降级重试")
        
        # 1. 先尝试缓存的成功选择器
        if strategy_name in self.cache.successful:
            cached = self.cache.successful[strategy_name]
            if cached in candidates:
                if self._try_find(cached, timeout):
                    return cached
        
        # 2. 按顺序尝试候选选择器
        for selector in candidates:
            if self._try_find(selector, timeout, text_filter):
                self._record_success(strategy_name, selector)
                return selector
            self._record_failure(strategy_name, selector)
        
        # 3. 降级：尝试文本搜索
        if text_filter:
            fallback = self._try_text_fallback(text_filter, timeout)
            if fallback:
                # 文本搜索成功也记住，但用特殊标记
                self.cache.successful[f"{strategy_name}_text"] = fallback
                self._save_cache()
                logger.info(f"✓ [{strategy_name}] 文本搜索成功: {fallback}")
                return fallback
        
        logger.error(f"✗ [{strategy_name}] 所有选择器都失败: {list(candidates)}")
        return None
    
    def _try_find(
        self,
        selector: str,
        timeout: int = 5000,
        text_filter: str = None
    ) -> bool:
        """尝试查找单个选择器"""
        start = time.time()
        try:
            if text_filter:
                # 带文本过滤的查找
                self.page.wait_for_selector(selector, timeout=timeout)
                element = self.page.locator(selector, has_text=text_filter)
                return element.count() > 0
            else:
                self.page.wait_for_selector(selector, timeout=timeout)
                return True
        except Exception as e:
            return False
    
    def _try_text_fallback(self, text: str, timeout: int = 5000) -> Optional[str]:
        """
        文本搜索降级
        
        尝试多种文本搜索方式
        """
        strategies = [
            # 普通文本包含
            f'text="{text}"',
            f'text={text}',
            # 部分文本
            f'text=/{text}/',
            # contains函数
            f'*:has-text("{text}")',
            # 正则
            f'text=/.*{text}.*/',
        ]
        
        for strategy in strategies:
            try:
                self.page.wait_for_selector(strategy, timeout=timeout)
                return strategy
            except:
                continue
        
        return None
    
    def click(
        self,
        strategy_name: str,
        *selectors: str,
        timeout: int = 5000,
        text_filter: str = None,
        retry: int = 1
    ) -> bool:
        """
        智能点击
        
        Args:
            strategy_name: 策略名称
            *selectors: 备选选择器
            timeout: 超时
            text_filter: 文本过滤
            retry: 重试次数
            
        Returns:
            是否成功
        """
        for attempt in range(retry):
            selector = self.find(strategy_name, *selectors, timeout=timeout, text_filter=text_filter)
            if selector:
                if self._try_click(selector):
                    return True
                self._record_failure(strategy_name, selector)
            time.sleep(0.5)
        
        return False
    
    def _try_click(self, selector: str, timeout: int = 3000) -> bool:
        """尝试点击"""
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            
            # 三阶段点击策略
            try:
                self.page.click(selector, timeout=timeout)
                return True
            except:
                pass
            
            try:
                self.page.locator(selector).first.click(timeout=timeout)
                return True
            except:
                pass
            
            try:
                # JavaScript点击兜底
                self.page.evaluate(f'''
                    document.querySelector('{selector}')?.click()
                ''')
                return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.warning(f"点击失败: {selector}, {e}")
            return False
    
    def type(
        self,
        strategy_name: str,
        text: str,
        *selectors: str,
        timeout: int = 5000,
        delay: int = 0,
        clear_first: bool = True
    ) -> bool:
        """
        智能输入
        
        Args:
            strategy_name: 策略名称
            text: 输入文本
            *selectors: 备选选择器
            timeout: 超时
            delay: 逐字输入延迟
            clear_first: 是否先清空
            
        Returns:
            是否成功
        """
        selector = self.find(strategy_name, *selectors, timeout=timeout)
        if not selector:
            return False
        
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
            
            if clear_first:
                self.page.fill(selector, '')
            
            if delay > 0:
                self.page.type(selector, text, delay=delay)
            else:
                self.page.fill(selector, text)
            
            self._record_success(f"{strategy_name}_type", selector)
            return True
            
        except Exception as e:
            logger.warning(f"输入失败: {selector}, {e}")
            self._record_failure(strategy_name, selector)
            return False
    
    def hover(self, strategy_name: str, *selectors: str, timeout: int = 5000) -> bool:
        """智能悬停"""
        selector = self.find(strategy_name, *selectors, timeout=timeout)
        if not selector:
            return False
        
        try:
            self.page.hover(selector)
            return True
        except:
            return False
    
    def is_visible(self, *selectors: str, timeout: int = 2000) -> Tuple[bool, Optional[str]]:
        """
        检查元素是否可见
        
        Returns:
            (是否可见, 匹配到的选择器)
        """
        for selector in selectors:
            try:
                self.page.wait_for_selector(selector, timeout=timeout)
                if self.page.locator(selector).first.is_visible():
                    return True, selector
            except:
                continue
        return False, None
    
    def wait_and_get(
        self,
        strategy_name: str,
        *selectors: str,
        timeout: int = 15000,
        poll_interval: float = 0.5
    ) -> bool:
        """
        等待元素出现
        
        Args:
            strategy_name: 策略名称
            *selectors: 备选选择器
            timeout: 总超时时间
            poll_interval: 轮询间隔
            
        Returns:
            是否在超时内出现
        """
        deadline = time.time() + timeout / 1000
        
        while time.time() < deadline:
            selector = self.find(strategy_name, *selectors, timeout=1000)
            if selector:
                return True
            time.sleep(poll_interval)
        
        return False
    
    def get_text(self, *selectors: str) -> Optional[str]:
        """获取元素文本"""
        for selector in selectors:
            try:
                element = self.page.wait_for_selector(selector, timeout=3000)
                if element:
                    return element.inner_text()
            except:
                continue
        return None
    
    def get_attribute(self, selector: str, attr: str) -> Optional[str]:
        """获取元素属性"""
        try:
            element = self.page.wait_for_selector(selector, timeout=3000)
            if element:
                return element.get_attribute(attr)
        except:
            pass
        return None
    
    # ==================== 缓存管理 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_strategies': len(self.cache.successful),
            'successful_selectors': len(self.cache.successful),
            'failed_attempts': sum(len(v) for v in self.cache.failed.values()),
            'total_attempts': sum(self.cache.attempt_counts.values()),
            'total_successes': sum(self.cache.success_counts.values()),
        }
    
    def invalidate_strategy(self, strategy_name: str):
        """使某个策略的缓存失效"""
        if strategy_name in self.cache.successful:
            del self.cache.successful[strategy_name]
        if strategy_name in self.cache.failed:
            del self.cache.failed[strategy_name]
        self._save_cache()
        logger.info(f"策略缓存已清除: {strategy_name}")
    
    def clear_all_cache(self):
        """清除所有缓存"""
        self.cache = SelectorCache()
        self._save_cache()
        logger.info("所有选择器缓存已清除")
    
    def export_cache(self) -> str:
        """导出缓存到JSON"""
        return json.dumps(self.cache.to_dict(), indent=2, ensure_ascii=False)
    
    def import_cache(self, json_str: str):
        """导入缓存"""
        try:
            data = json.loads(json_str)
            self.cache = SelectorCache.from_dict(data)
            self._save_cache()
            logger.info("缓存导入成功")
        except Exception as e:
            logger.error(f"缓存导入失败: {e}")


class ZhixiaSelectors:
    """
    知虾网站专用选择器
    
    预定义知虾网站常用的选择器策略
    """
    
    def __init__(self, adaptive: AdaptiveSelector):
        self.adaptive = adaptive
    
    @property
    def page(self):
        return self.adaptive.page
    
    # ==================== 搜索相关 ====================
    
    def click_search_tab(self) -> bool:
        """点击搜索标签"""
        return self.adaptive.click(
            'search_tab',
            'text=搜商品',
            'a:has-text("搜商品")',
            '[class*="search"] a',
            'a:has-text("搜索")',
            text_filter='搜商品'
        )
    
    def type_keyword(self, keyword: str) -> bool:
        """输入搜索关键词"""
        return self.adaptive.type(
            'keyword_input',
            keyword,
            'input[placeholder*="关键词"]',
            'input[placeholder*="keyword"]',
            'input[placeholder*="搜索"]',
            'input[class*="search"]',
            'input[type="text"]'
        )
    
    def click_search_button(self) -> bool:
        """点击搜索按钮"""
        return self.adaptive.click(
            'search_btn',
            'button:has-text("搜索")',
            'button:has-text("查询")',
            '[class*="search"] button',
            'button:has-text("搜")',
            'button[type="submit"]'
        )
    
    # ==================== 站点选择 ====================
    
    def click_site_dropdown(self) -> bool:
        """点击站点下拉框"""
        return self.adaptive.click(
            'site_dropdown',
            'button:has-text("站点")',
            '[class*="site"] button',
            '[class*="region"] button',
            'select[class*="site"]',
            text_filter='站点'
        )
    
    def select_site(self, site_name: str) -> bool:
        """选择站点"""
        # 先点击下拉框
        if not self.click_site_dropdown():
            return False
        
        time.sleep(0.5)
        
        # 点击目标站点
        return self.adaptive.click(
            f'site_{site_name}',
            f'text={site_name}',
            f'li:has-text("{site_name}")',
            f'option:has-text("{site_name}")',
            f'*[class*="option"]:has-text("{site_name}")'
        )
    
    # ==================== 导出相关 ====================
    
    def click_export(self) -> bool:
        """点击导出按钮"""
        return self.adaptive.click(
            'export_btn',
            'button:has-text("导出")',
            'button:has-text("导出Excel")',
            '[class*="export"]',
            'a:has-text("导出")',
            '[aria-label*="导出"]',
            text_filter='导出'
        )
    
    def click_export_confirm(self) -> bool:
        """点击导出确认"""
        return self.adaptive.click(
            'export_confirm',
            'button:has-text("确定")',
            'button:has-text("确认")',
            'button:has-text("下载")',
            'button:has-text("yes")',
            'button:has-text("是")',
            text_filter='确定'
        )
    
    # ==================== 页面导航 ====================
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        # 检查URL
        url = self.page.url.lower()
        login_indicators = ['/login', 'signin', 'passport', 'auth']
        
        if any(ind in url for ind in login_indicators):
            return False
        
        # 检查页面内容
        try:
            text = self.page.inner_text('body', timeout=2000)
            if '请登录' in text[:200]:
                return False
        except:
            pass
        
        return True
    
    def wait_page_loaded(self, timeout: int = 15000) -> bool:
        """等待页面加载完成"""
        try:
            self.page.wait_for_load_state('networkidle', timeout=timeout)
            return True
        except:
            pass
        
        try:
            self.page.wait_for_load_state('domcontentloaded', timeout=5000)
            return True
        except:
            pass
        
        time.sleep(3)
        return True
    
    def wait_for_results(self, timeout: int = 15000) -> bool:
        """等待搜索结果加载"""
        result_indicators = [
            '[class*="result"]',
            '[class*="table"]',
            '[class*="list"]',
            '[class*="data"]',
            'text=/\\d+条/',
            'text=/\\d+个/',
        ]
        
        for indicator in result_indicators:
            if self.adaptive.wait_and_get('results', indicator, timeout=timeout):
                return True
        
        # 等待足够时间后返回
        time.sleep(min(timeout / 1000, 10))
        return True
