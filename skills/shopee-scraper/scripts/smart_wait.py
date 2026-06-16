#!/usr/bin/env python3
"""
智能等待模块
核心特性：
1. 自适应等待时间 - 根据历史调整
2. 多种等待条件 - 元素、网络、空闲
3. 快速失败 - 超时立即返回
4. 重试机制 - 偶发失败自动重试
"""
import os
import time
import logging
from typing import Optional, Callable, Any, List
from dataclasses import dataclass, field
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class WaitStats:
    """等待统计"""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_wait_time: float = 0.0
    average_wait_time: float = 0.0
    
    def record(self, success: bool, wait_time: float):
        """记录一次等待"""
        self.total_attempts += 1
        if success:
            self.successful_attempts += 1
        else:
            self.failed_attempts += 1
        self.total_wait_time += wait_time
        if self.total_attempts > 0:
            self.average_wait_time = self.total_wait_time / self.total_attempts


@dataclass
class WaitHistory:
    """等待历史"""
    histories: dict = field(default_factory=dict)  # condition -> WaitStats
    
    def record(self, condition: str, success: bool, wait_time: float):
        if condition not in self.histories:
            self.histories[condition] = WaitStats()
        self.histories[condition].record(success, wait_time)
    
    def get_suggested_timeout(self, condition: str, default: int = 10) -> int:
        """根据历史获取建议的超时时间"""
        if condition in self.histories:
            stats = self.histories[condition]
            if stats.successful_attempts > 0:
                # 使用平均等待时间的1.5倍作为超时
                return max(int(stats.average_wait_time * 1.5), 2)
        return default
    
    def to_dict(self) -> dict:
        return {
            'histories': {
                k: {
                    'total': v.total_attempts,
                    'success': v.successful_attempts,
                    'fail': v.failed_attempts,
                    'avg_time': round(v.average_wait_time, 2),
                }
                for k, v in self.histories.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WaitHistory':
        history = cls()
        for k, v in data.get('histories', {}).items():
            history.histories[k] = WaitStats(
                total_attempts=v.get('total', 0),
                successful_attempts=v.get('success', 0),
                failed_attempts=v.get('fail', 0),
            )
        return history


class SmartWait:
    """
    智能等待器
    
    核心策略：
    1. 快速检测 - 先尝试短超时探测
    2. 自适应 - 根据历史调整等待时间
    3. 多种条件 - 元素、网络、函数
    4. 记录学习 - 记住成功经验
    """
    
    def __init__(self, page, cache_dir: str = None):
        """
        初始化智能等待器
        
        Args:
            page: Playwright Page对象
            cache_dir: 缓存目录
        """
        self.page = page
        self.cache_dir = Path(cache_dir) if cache_dir else Path('.')
        self.history_file = self.cache_dir / 'wait_history.json'
        
        # 加载历史
        self.history = self._load_history()
    
    def _load_history(self) -> WaitHistory:
        """加载等待历史"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return WaitHistory.from_dict(json.load(f))
            except Exception as e:
                logger.warning(f"加载等待历史失败: {e}")
        return WaitHistory()
    
    def _save_history(self):
        """保存等待历史"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump(self.history.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"保存等待历史失败: {e}")
    
    # ==================== 核心等待方法 ====================
    
    def for_element(
        self,
        selector: str,
        timeout: int = None,
        state: str = 'visible'
    ) -> bool:
        """
        智能等待元素
        
        Args:
            selector: CSS选择器或文本选择器
            timeout: 超时时间（秒），None则自动
            state: 元素状态 ('attached', 'detached', 'visible', 'hidden')
            
        Returns:
            是否在超时内出现
        """
        # 自动超时
        if timeout is None:
            timeout = self.history.get_suggested_timeout(f"element_{selector[:30]}", 10)
        
        start_time = time.time()
        condition_name = f"element_{selector[:30]}_{state}"
        
        try:
            self.page.wait_for_selector(
                selector,
                timeout=timeout * 1000,
                state=state
            )
            
            wait_time = time.time() - start_time
            self.history.record(condition_name, True, wait_time)
            self._save_history()
            
            return True
            
        except Exception as e:
            wait_time = time.time() - start_time
            self.history.record(condition_name, False, wait_time)
            self._save_history()
            
            logger.warning(f"等待元素超时: {selector}, 耗时: {wait_time:.1f}s")
            return False
    
    def for_elements(
        self,
        selector: str,
        min_count: int = 1,
        timeout: int = 15
    ) -> int:
        """
        等待元素数量达到要求
        
        Args:
            selector: 选择器
            min_count: 最少元素数量
            timeout: 超时时间
            
        Returns:
            实际元素数量
        """
        start_time = time.time()
        deadline = start_time + timeout
        
        while time.time() < deadline:
            try:
                elements = self.page.query_selector_all(selector)
                count = len(elements)
                
                if count >= min_count:
                    wait_time = time.time() - start_time
                    self.history.record(f"elements_{selector[:30]}", True, wait_time)
                    return count
                    
            except Exception:
                pass
            
            time.sleep(0.5)
        
        wait_time = time.time() - start_time
        self.history.record(f"elements_{selector[:30]}", False, wait_time)
        
        try:
            return len(self.page.query_selector_all(selector))
        except:
            return 0
    
    def for_network_idle(self, timeout: int = 10) -> bool:
        """
        智能等待网络空闲
        
        策略：
        1. 先尝试短超时（3秒）
        2. 失败则尝试完整超时
        3. 仍然失败则降级到固定等待
        """
        # 策略1: 快速检测
        try:
            self.page.wait_for_load_state('networkidle', timeout=3000)
            self.history.record('network_idle', True, 3)
            return True
        except:
            pass
        
        # 策略2: 完整超时
        try:
            start = time.time()
            self.page.wait_for_load_state('networkidle', timeout=timeout * 1000)
            wait_time = time.time() - start
            self.history.record('network_idle', True, wait_time)
            return True
        except:
            pass
        
        # 策略3: 降级等待
        time.sleep(min(timeout, 5))
        self.history.record('network_idle', False, timeout)
        return True
    
    def for_function(
        self,
        func: Callable[[], bool],
        timeout: int = 15,
        poll_interval: float = 0.5
    ) -> bool:
        """
        等待函数返回True
        
        Args:
            func: 返回bool的函数
            timeout: 超时时间
            poll_interval: 轮询间隔
            
        Returns:
            函数是否返回True
        """
        start_time = time.time()
        deadline = start_time + timeout
        
        while time.time() < deadline:
            try:
                if func():
                    wait_time = time.time() - start_time
                    self.history.record('function', True, wait_time)
                    return True
            except Exception as e:
                logger.debug(f"等待函数异常: {e}")
            
            time.sleep(poll_interval)
        
        wait_time = time.time() - start_time
        self.history.record('function', False, wait_time)
        return False
    
    def for_url(
        self,
        url_pattern: str,
        timeout: int = 30,
        contains: bool = True
    ) -> bool:
        """
        等待URL变化
        
        Args:
            url_pattern: URL模式
            timeout: 超时时间
            contains: True则包含匹配，False则完全匹配
            
        Returns:
            是否匹配
        """
        start_time = time.time()
        
        def check_url():
            url = self.page.url
            if contains:
                return url_pattern in url
            else:
                return url == url_pattern
        
        # 先检查当前URL
        if check_url():
            return True
        
        return self.for_function(check_url, timeout)
    
    def for_text(
        self,
        text: str,
        selector: str = 'body',
        timeout: int = 15
    ) -> bool:
        """
        等待文本出现
        
        Args:
            text: 要等待的文本
            selector: 在哪个元素中查找
            timeout: 超时时间
            
        Returns:
            是否出现
        """
        def check_text():
            try:
                element = self.page.query_selector(selector)
                if element:
                    content = element.inner_text()
                    return text in content
            except:
                pass
            return False
        
        return self.for_function(check_text, timeout)
    
    def for_no_element(
        self,
        selector: str,
        timeout: int = 10
    ) -> bool:
        """
        等待元素消失
        
        Args:
            selector: 元素选择器
            timeout: 超时时间
            
        Returns:
            元素是否消失
        """
        start_time = time.time()
        deadline = start_time + timeout
        
        while time.time() < deadline:
            try:
                element = self.page.query_selector(selector)
                if not element or not element.is_visible():
                    wait_time = time.time() - start_time
                    self.history.record(f"no_element_{selector[:30]}", True, wait_time)
                    return True
            except:
                return True  # 查询失败认为元素不存在
            
            time.sleep(0.5)
        
        wait_time = time.time() - start_time
        self.history.record(f"no_element_{selector[:30]}", False, wait_time)
        return False
    
    # ==================== 便捷方法 ====================
    
    def sleep(self, seconds: float):
        """固定等待"""
        time.sleep(seconds)
    
    def smart_sleep(self, base: float = 2, max_wait: float = 10) -> float:
        """
        智能固定等待
        
        根据历史自动调整等待时间
        
        Args:
            base: 基础等待时间
            max_wait: 最大等待时间
            
        Returns:
            实际等待时间
        """
        suggested = self.history.get_suggested_timeout('sleep', int(base))
        wait_time = min(suggested, max_wait)
        time.sleep(wait_time)
        return wait_time
    
    # ==================== 统计和工具 ====================
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.history.to_dict()
    
    def clear_history(self):
        """清除历史记录"""
        self.history = WaitHistory()
        self._save_history()
        logger.info("等待历史已清除")


class RetryHandler:
    """
    多级重试处理器
    
    支持：
    1. 多种重试策略
    2. 退避算法
    3. 条件重试
    """
    
    STRATEGIES = {
        'quick': {'retries': 2, 'delay': 0.5, 'backoff': 1.5, 'max_delay': 3},
        'normal': {'retries': 3, 'delay': 1, 'backoff': 2, 'max_delay': 10},
        'slow': {'retries': 5, 'delay': 2, 'backoff': 2, 'max_delay': 30},
    }
    
    def __init__(self, strategy: str = 'normal'):
        self.strategy_config = self.STRATEGIES.get(strategy, self.STRATEGIES['normal'])
    
    def execute(
        self,
        func: Callable,
        *args,
        on_retry: Callable[[int, Exception], None] = None,
        should_retry: Callable[[Exception], bool] = None,
        **kwargs
    ) -> Any:
        """
        执行带重试的函数
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            on_retry: 重试回调 (attempt, error)
            should_retry: 判断是否应该重试 (error) -> bool
            **kwargs: 函数关键字参数
            
        Returns:
            函数返回值
            
        Raises:
            最后一次重试的异常
        """
        cfg = self.strategy_config
        last_error = None
        
        for attempt in range(cfg['retries']):
            try:
                return func(*args, **kwargs)
                
            except Exception as e:
                last_error = e
                
                # 检查是否应该重试
                if should_retry and not should_retry(e):
                    raise e
                
                # 检查是否还有重试次数
                if attempt >= cfg['retries'] - 1:
                    break
                
                # 计算延迟
                delay = min(
                    cfg['delay'] * (cfg['backoff'] ** attempt),
                    cfg['max_delay']
                )
                
                # 回调
                if on_retry:
                    on_retry(attempt + 1, e)
                
                logger.warning(f"重试 {attempt + 1}/{cfg['retries']}, 等待 {delay:.1f}s: {e}")
                time.sleep(delay)
        
        if last_error:
            raise last_error


def retry_on_exception(func=None, strategy: str = 'normal', exceptions: tuple = (Exception,)):
    """
    重试装饰器
    
    Usage:
        @retry_on_exception(strategy='normal')
        def my_function():
            ...
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            handler = RetryHandler(strategy)
            
            def should_retry(e):
                return isinstance(e, exceptions)
            
            return handler.execute(f, *args, should_retry=should_retry, **kwargs)
        
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)
