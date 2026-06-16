#!/usr/bin/env python3
"""
优化版知虾采集器
核心特性：
1. 自适应选择器 - 页面改版不怕
2. 智能等待 - 不白等也不等不够
3. 断点续传 - 中断后可继续
4. 多级重试 - 偶发错误自动恢复
"""
import os
import sys
import time
import json
import yaml
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

from optimized_login_manager import OptimizedLoginManager
from adaptive_selector import AdaptiveSelector, ZhixiaSelectors
from smart_wait import SmartWait, RetryHandler

logger = logging.getLogger(__name__)


class ProgressCheckpoint:
    """
    进度检查点
    
    用于断点续传
    """
    
    def __init__(self, task_id: str, checkpoint_dir: str = None):
        self.task_id = task_id
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else Path('.cache')
        self.checkpoint_file = self.checkpoint_dir / f"checkpoint_{task_id}.json"
        
        self.state = self._load()
    
    def _load(self) -> dict:
        """加载检查点"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'task_id': self.task_id,
            'start_time': None,
            'completed': [],
            'failed': {},
            'last_update': None,
        }
    
    def _save(self):
        """保存检查点"""
        self.state['last_update'] = time.time()
        
        try:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.warning(f"检查点保存失败: {e}")
    
    def start(self, total_tasks: int):
        """开始任务"""
        self.state['start_time'] = time.time()
        self.state['total_tasks'] = total_tasks
        self._save()
    
    def mark_complete(self, task_key: str):
        """标记任务完成"""
        if task_key not in self.state['completed']:
            self.state['completed'].append(task_key)
        if task_key in self.state['failed']:
            del self.state['failed'][task_key]
        self._save()
    
    def mark_failed(self, task_key: str, error: str):
        """标记任务失败"""
        self.state['failed'][task_key] = {
            'error': error,
            'time': time.time(),
        }
        self._save()
    
    def is_completed(self, task_key: str) -> bool:
        """检查任务是否完成"""
        return task_key in self.state['completed']
    
    def get_remaining(self, all_tasks: List[str]) -> List[str]:
        """获取剩余任务"""
        return [t for t in all_tasks if t not in self.state['completed']]
    
    def get_progress(self) -> Tuple[int, int]:
        """获取进度"""
        total = self.state.get('total_tasks', 0)
        completed = len(self.state.get('completed', []))
        return completed, total
    
    def clear(self):
        """清除检查点"""
        self.state = {
            'task_id': self.task_id,
            'start_time': None,
            'completed': [],
            'failed': {},
            'last_update': None,
        }
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()


class OptimizedZhixiaScraper:
    """
    优化版知虾采集器
    
    整合所有优化模块：
    1. OptimizedLoginManager - 快速登录
    2. AdaptiveSelector - 自适应选择器
    3. SmartWait - 智能等待
    4. ProgressCheckpoint - 断点续传
    """
    
    # 站点映射
    SITE_MAP = {
        'MY': '马来西亚',
        'ID': '印尼',
        'TH': '泰国',
        'PH': '菲律宾',
        'SG': '新加坡',
        'VN': '越南',
    }
    
    # 站点URL映射
    SITE_URL_MAP = {
        'MY': 'shopee.com.my',
        'ID': 'shopee.co.id',
        'TH': 'shopee.co.th',
        'PH': 'shopee.ph',
        'SG': 'shopee.sg',
        'VN': 'shopee.vn',
    }
    
    def __init__(self, config_path: str = None, cache_dir: str = None):
        """
        初始化采集器
        
        Args:
            config_path: 配置文件路径
            cache_dir: 缓存目录
        """
        # 路径设置
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if config_path is None:
            config_path = os.path.join(base_dir, 'config', 'competitors.yaml')
        if cache_dir is None:
            cache_dir = os.path.join(base_dir, 'data', 'cache')
        
        self.config = self._load_config(config_path)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 登录管理器
        cookie_file = os.path.join(base_dir, 'data', 'cookies.json')
        screenshot_dir = os.path.join(base_dir, 'data', 'screenshots')
        
        self.login_manager = OptimizedLoginManager(
            cookie_file=cookie_file,
            screenshot_dir=screenshot_dir,
            cache_dir=str(self.cache_dir)
        )
        
        # 核心对象
        self.page = None
        self.selectors: Optional[ZhixiaSelectors] = None
        self.waiter: Optional[SmartWait] = None
        self.retry = RetryHandler('normal')
        
        # 下载目录
        download_dir = self.config.get('browser', {}).get('download_dir', 'data/downloads')
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"配置加载失败: {e}")
            return {}
    
    # ==================== 生命周期 ====================
    
    def initialize(self) -> Tuple[bool, str]:
        """
        初始化采集器
        
        Returns:
            (是否成功, 原因)
        """
        logger.info("初始化优化版知虾采集器...")
        
        # 确保登录
        success, reason = self.login_manager.ensure_login()
        
        if not success:
            return False, f"登录失败: {reason}"
        
        # 获取页面
        self.page = self.login_manager.get_page()
        
        if not self.page:
            return False, "无法获取页面"
        
        # 初始化选择器
        adaptive = AdaptiveSelector(
            page=self.page,
            cache_dir=str(self.cache_dir),
            cache_prefix='zhixia'
        )
        self.selectors = ZhixiaSelectors(adaptive)
        
        # 初始化等待器
        self.waiter = SmartWait(
            page=self.page,
            cache_dir=str(self.cache_dir)
        )
        
        logger.info("初始化成功")
        return True, reason
    
    def close(self):
        """关闭采集器"""
        self.login_manager.close_browser(save_cookies=True)
    
    # ==================== 导航 ====================
    
    def navigate_to_search(self) -> bool:
        """导航到搜索页面"""
        logger.info("导航到搜索页面...")
        
        base_url = self.config.get('zhixia', {}).get('base_url', 'https://shopee.menglar.com')
        search_url = f"{base_url}/workbench/search/keyword-fuzzy-search?type=1"
        
        try:
            self.page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            self.waiter.sleep(3)
            
            # 等待页面加载
            self.selectors.wait_page_loaded(timeout=15)
            
            return True
        except Exception as e:
            logger.error(f"导航失败: {e}")
            return False
    
    # ==================== 搜索操作 ====================
    
    def search_keyword(self, keyword: str, retry: int = 2) -> bool:
        """
        搜索关键词
        
        Args:
            keyword: 关键词
            retry: 重试次数
            
        Returns:
            是否成功
        """
        logger.info(f"搜索关键词: {keyword}")
        
        for attempt in range(retry):
            try:
                # 点击搜索标签
                if not self.selectors.click_search_tab():
                    logger.warning(f"尝试 {attempt+1}: 点击搜索标签失败")
                    self.waiter.sleep(1)
                    continue
                
                self.waiter.sleep(1)
                
                # 输入关键词
                if not self.selectors.type_keyword(keyword):
                    logger.warning(f"尝试 {attempt+1}: 输入关键词失败")
                    self.waiter.sleep(1)
                    continue
                
                self.waiter.sleep(0.5)
                
                # 点击搜索按钮
                if not self.selectors.click_search_button():
                    logger.warning(f"尝试 {attempt+1}: 点击搜索按钮失败")
                    self.waiter.sleep(1)
                    continue
                
                # 等待结果
                self.waiter.sleep(5)
                if self.selectors.wait_for_results(timeout=20):
                    logger.info("搜索成功")
                    return True
                
            except Exception as e:
                logger.warning(f"搜索异常: {e}")
                self.waiter.sleep(2)
        
        return False
    
    def select_site(self, site_code: str) -> bool:
        """
        选择站点
        
        Args:
            site_code: 站点代码 (MY, ID, TH等)
            
        Returns:
            是否成功
        """
        site_name = self.SITE_MAP.get(site_code, site_code)
        logger.info(f"选择站点: {site_code} ({site_name})")
        
        # 使用重试
        def _do_select():
            return self.selectors.select_site(site_name)
        
        try:
            return self.retry.execute(_do_select, should_retry=lambda e: False)
        except:
            return self.selectors.select_site(site_name)
    
    # ==================== 导出操作 ====================
    
    def click_export(self, retry: int = 2) -> bool:
        """
        点击导出按钮
        
        Args:
            retry: 重试次数
            
        Returns:
            是否成功
        """
        logger.info("点击导出...")
        
        for attempt in range(retry):
            try:
                if self.selectors.click_export():
                    self.waiter.sleep(2)
                    
                    # 处理可能的确认弹窗
                    self.selectors.click_export_confirm()
                    
                    logger.info("导出按钮点击成功")
                    return True
                    
            except Exception as e:
                logger.warning(f"导出尝试 {attempt+1} 失败: {e}")
                self.waiter.sleep(1)
        
        return False
    
    def wait_for_download(self, timeout: int = 30) -> Optional[str]:
        """
        等待下载完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            下载文件路径或None
        """
        logger.info("等待下载...")
        
        # 记录下载前的文件
        before_files = set(self.download_dir.glob('*.xlsx'))
        before_files.update(self.download_dir.glob('*.xls'))
        
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            # 检查新文件
            after_files = set(self.download_dir.glob('*.xlsx'))
            after_files.update(self.download_dir.glob('*.xls'))
            
            new_files = after_files - before_files
            
            if new_files:
                # 等待文件写入完成
                time.sleep(1)
                
                for f in new_files:
                    if f.stat().st_size > 1000:  # 文件大小大于1KB
                        logger.info(f"下载完成: {f.name}")
                        return str(f)
            
            time.sleep(1)
        
        logger.warning("下载超时")
        return None
    
    # ==================== 完整采集流程 ====================
    
    def scrape_site_keyword(
        self,
        site: str,
        keyword: str,
        product_line: str = None
    ) -> Tuple[bool, str]:
        """
        采集单个站点+关键词
        
        Args:
            site: 站点代码
            keyword: 关键词
            product_line: 产品线代码
            
        Returns:
            (是否成功, 结果/错误信息)
        """
        task_key = f"{site}_{keyword}"
        logger.info(f"开始采集: {task_key}")
        
        try:
            # 导航到搜索页
            if not self.navigate_to_search():
                return False, "导航到搜索页失败"
            
            # 选择站点
            if not self.select_site(site):
                logger.warning(f"站点选择可能失败: {site}")
            
            # 搜索关键词
            if not self.search_keyword(keyword):
                return False, "搜索失败"
            
            # 点击导出
            if not self.click_export():
                return False, "导出失败"
            
            # 等待下载
            filepath = self.wait_for_download(timeout=30)
            
            if filepath:
                return True, filepath
            else:
                return False, "下载超时"
                
        except Exception as e:
            logger.error(f"采集异常: {e}")
            return False, str(e)
    
    def scrape_multiple(
        self,
        sites: List[str],
        keywords: List[str],
        product_lines: Dict[str, str] = None,
        resume: bool = True
    ) -> Dict[str, Any]:
        """
        批量采集
        
        Args:
            sites: 站点列表
            keywords: 关键词列表
            product_lines: 产品线映射
            resume: 是否断点续传
            
        Returns:
            采集结果
        """
        if product_lines is None:
            product_lines = {}
        
        # 生成任务列表
        tasks = []
        for site in sites:
            for keyword in keywords:
                task_key = f"{site}_{keyword}"
                tasks.append({
                    'key': task_key,
                    'site': site,
                    'keyword': keyword,
                    'product_line': product_lines.get(keyword, ''),
                })
        
        # 初始化检查点
        checkpoint = ProgressCheckpoint(
            task_id='zhixia_scrape',
            checkpoint_dir=str(self.cache_dir)
        )
        
        # 获取剩余任务
        if resume:
            remaining_tasks = checkpoint.get_remaining([t['key'] for t in tasks])
            tasks = [t for t in tasks if t['key'] in remaining_tasks]
            completed, total = checkpoint.get_progress()
            logger.info(f"断点续传: 已完成 {completed}/{total}, 本次执行 {len(tasks)} 个任务")
        else:
            checkpoint.clear()
            checkpoint.start(len(tasks))
            logger.info(f"新任务: 共 {len(tasks)} 个任务")
        
        # 执行采集
        results = {
            'total': len(tasks),
            'completed': 0,
            'failed': 0,
            'files': [],
            'errors': [],
        }
        
        for task in tasks:
            logger.info(f"[{task['key']}] 进度: {results['completed']+results['failed']}/{len(tasks)}")
            
            success, result = self.scrape_site_keyword(
                site=task['site'],
                keyword=task['keyword'],
                product_line=task['product_line']
            )
            
            if success:
                results['completed'] += 1
                results['files'].append(result)
                checkpoint.mark_complete(task['key'])
                logger.info(f"✓ {task['key']} 成功")
            else:
                results['failed'] += 1
                results['errors'].append({
                    'task': task['key'],
                    'error': result,
                })
                checkpoint.mark_failed(task['key'], result)
                logger.error(f"✗ {task['key']} 失败: {result}")
            
            # 任务间隔
            self.waiter.sleep(2)
        
        # 统计
        results['total_completed'] = results['completed'] + checkpoint.state.get('completed', [])
        results['success_rate'] = results['completed'] / len(tasks) * 100 if tasks else 0
        
        logger.info(f"采集完成: 成功 {results['completed']}, 失败 {results['failed']}, 成功率 {results['success_rate']:.1f}%")
        
        return results
    
    # ==================== 工具方法 ====================
    
    def get_downloaded_files(self, pattern: str = '*') -> List[str]:
        """获取下载的文件"""
        files = list(self.download_dir.glob(f'{pattern}.xlsx'))
        files.extend(self.download_dir.glob(f'{pattern}.xls'))
        return [str(f) for f in files]
    
    def get_selector_stats(self) -> Dict:
        """获取选择器统计"""
        if self.selectors and self.selectors.adaptive:
            return self.selectors.adaptive.get_stats()
        return {}
    
    def get_wait_stats(self) -> Dict:
        """获取等待统计"""
        if self.waiter:
            return self.waiter.get_stats()
        return {}
    
    def clear_cache(self):
        """清除缓存"""
        if self.selectors and self.selectors.adaptive:
            self.selectors.adaptive.clear_all_cache()
        if self.waiter:
            self.waiter.clear_history()
        logger.info("缓存已清除")


# ==================== 命令行入口 ====================

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='优化版知虾采集器')
    parser.add_argument('--sites', '-s', nargs='+', help='站点列表')
    parser.add_argument('--keywords', '-k', nargs='+', help='关键词列表')
    parser.add_argument('--config', '-c', help='配置文件')
    parser.add_argument('--no-resume', action='store_true', help='不使用断点续传')
    
    args = parser.parse_args()
    
    # 默认值
    if not args.sites:
        args.sites = ['MY', 'ID']
    if not args.keywords:
        args.keywords = ['insta360', '手机云台']
    
    # 创建采集器
    scraper = OptimizedZhixiaScraper(config_path=args.config)
    
    try:
        # 初始化
        success, reason = scraper.initialize()
        if not success:
            print(f"初始化失败: {reason}")
            sys.exit(1)
        
        print(f"初始化成功: {reason}")
        
        # 执行采集
        results = scraper.scrape_multiple(
            sites=args.sites,
            keywords=args.keywords,
            resume=not args.no_resume
        )
        
        # 输出结果
        print("\n" + "=" * 50)
        print("采集结果:")
        print(f"  总任务: {results['total']}")
        print(f"  成功: {results['completed']}")
        print(f"  失败: {results['failed']}")
        print(f"  成功率: {results['success_rate']:.1f}%")
        print(f"\n下载文件:")
        for f in results['files']:
            print(f"  - {f}")
        print("=" * 50)
        
    finally:
        scraper.close()


if __name__ == '__main__':
    main()
