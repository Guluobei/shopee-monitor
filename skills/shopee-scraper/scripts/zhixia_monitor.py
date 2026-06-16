#!/usr/bin/env python3
"""
知虾竞品监控 - 优化版主程序
整合传统和新版优化模块，提供流畅的采集体验
"""
import os
import sys
import json
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 添加scripts目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from optimized_scraper import OptimizedZhixiaScraper
from optimized_login_manager import OptimizedLoginManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ZhixiaMonitor:
    """
    知虾竞品监控器 - 优化版
    
    支持：
    1. 快速登录（Cookie缓存 + 快速验证）
    2. 断点续传
    3. 自适应选择器
    4. 智能等待
    """
    
    def __init__(self, config_path: str = None, use_optimized: bool = True):
        """
        初始化监控器
        
        Args:
            config_path: 配置文件路径
            use_optimized: 是否使用优化版模块
        """
        # 路径设置
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if config_path is None:
            config_path = os.path.join(base_dir, 'config', 'competitors.yaml')
        
        self.config = self._load_config(config_path)
        self.config_path = config_path
        self.use_optimized = use_optimized
        
        # 输出目录
        self.output_dir = Path(base_dir) / 'output'
        self.output_dir.mkdir(exist_ok=True)
        
        # 日志目录
        self.log_dir = Path(base_dir) / 'logs'
        self.log_dir.mkdir(exist_ok=True)
        
        # scraper
        self.scraper: Optional[OptimizedZhixiaScraper] = None
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            return {}
    
    def _save_log(self, task_type: str, data: Dict) -> str:
        """保存日志"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.log_dir / f'{task_type}_{timestamp}.json'
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(log_file)
    
    def _init_scraper(self) -> bool:
        """初始化采集器"""
        if self.scraper is None:
            self.scraper = OptimizedZhixiaScraper(
                config_path=self.config_path
            )
            
            success, reason = self.scraper.initialize()
            
            if not success:
                logger.error(f"初始化失败: {reason}")
                return False
        
        return True
    
    # ==================== 核心功能 ====================
    
    def login(self, force: bool = False) -> Dict:
        """
        登录
        
        Args:
            force: 是否强制重新登录
            
        Returns:
            登录结果
        """
        logger.info("=" * 50)
        logger.info("开始登录流程")
        logger.info("=" * 50)
        
        try:
            # 确保scraper初始化
            if not self._init_scraper():
                return {
                    'success': False,
                    'error': '初始化失败'
                }
            
            # 获取状态
            status = self.scraper.login_manager.get_status()
            
            return {
                'success': True,
                'state': status.get('state'),
                'cookie_status': status.get('cookie_status', {}),
                'session_valid': status.get('session_valid'),
                'message': '登录成功' if status.get('session_valid') else '需要登录'
            }
            
        except Exception as e:
            logger.error(f"登录异常: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def collect(
        self,
        sites: List[str] = None,
        product_lines: List[str] = None,
        keywords: List[str] = None,
        headless: bool = False,
        resume: bool = True
    ) -> Dict:
        """
        采集数据
        
        Args:
            sites: 站点列表
            product_lines: 产品线列表
            keywords: 关键词列表
            headless: 是否使用无头模式
            resume: 是否断点续传
            
        Returns:
            采集结果
        """
        logger.info("=" * 50)
        logger.info("开始数据采集")
        logger.info(f"站点: {sites or '全部'}")
        logger.info(f"产品线: {product_lines or '全部'}")
        logger.info(f"关键词: {keywords or '默认'}")
        logger.info("=" * 50)
        
        results = {
            'task': 'collect',
            'start_time': datetime.now().isoformat(),
            'status': 'pending',
            'files': [],
            'errors': [],
        }
        
        try:
            # 初始化采集器
            if not self._init_scraper():
                results['status'] = 'error'
                results['error'] = '初始化失败'
                return results
            
            # 确定站点
            if not sites:
                sites = [s['code'] for s in self.config.get('sites', [])]
            
            # 确定关键词
            if not keywords:
                keywords = []
                if product_lines:
                    for pl in product_lines:
                        pl_config = self.config.get('product_lines', {}).get(pl, {})
                        keywords.extend(pl_config.get('keywords', []))
                else:
                    for pl_config in self.config.get('product_lines', {}).values():
                        keywords.extend(pl_config.get('keywords', []))
            
            # 产品线映射
            product_line_map = {}
            for pl, pl_config in self.config.get('product_lines', {}).items():
                for kw in pl_config.get('keywords', []):
                    product_line_map[kw] = pl
            
            # 执行采集
            scrape_results = self.scraper.scrape_multiple(
                sites=sites,
                keywords=keywords,
                product_lines=product_line_map,
                resume=resume
            )
            
            results.update(scrape_results)
            results['status'] = 'completed' if scrape_results['failed'] == 0 else 'partial'
            
            # 获取下载的文件
            download_dir = self.scraper.download_dir
            files = list(download_dir.glob('*.xlsx'))
            files.extend(download_dir.glob('*.xls'))
            today = datetime.now().strftime('%Y%m%d')
            
            results['files'] = [
                str(f) for f in files 
                if today in f.name
            ]
            
            # 保存日志
            log_file = self._save_log('collect', results)
            results['log_file'] = log_file
            
            logger.info(f"采集完成: 成功 {results['completed']}, 失败 {results['failed']}")
            
        except Exception as e:
            logger.error(f"采集异常: {e}")
            results['status'] = 'error'
            results['error'] = str(e)
        
        finally:
            if self.scraper:
                self.scraper.close()
                self.scraper = None
        
        return results
    
    def process(self, download_dir: str = None) -> Dict:
        """
        处理数据
        
        Args:
            download_dir: 下载目录
            
        Returns:
            处理结果
        """
        logger.info("=" * 50)
        logger.info("开始数据处理")
        logger.info("=" * 50)
        
        results = {
            'task': 'process',
            'start_time': datetime.now().isoformat(),
            'status': 'pending',
        }
        
        try:
            # 延迟导入处理模块
            from data_processor import DataProcessor
            
            if download_dir is None:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                download_dir = os.path.join(base_dir, 'data', 'downloads')
            
            processor = DataProcessor(config_path=self.config_path)
            
            # 合并数据
            df = processor.merge_all_data(download_dir=download_dir)
            
            if df is not None and not df.empty:
                # 导出CSV
                csv_file = processor.export_to_csv(df)
                
                # 导出摘要
                summary_file = processor.export_summary(df)
                
                results.update({
                    'status': 'completed',
                    'records': len(df),
                    'csv_file': csv_file,
                    'summary_file': summary_file,
                })
                
                logger.info(f"处理完成: {len(df)} 条记录")
            else:
                results.update({
                    'status': 'warning',
                    'message': '没有找到数据'
                })
            
            # 保存日志
            log_file = self._save_log('process', results)
            results['log_file'] = log_file
            
        except Exception as e:
            logger.error(f"处理异常: {e}")
            results['status'] = 'error'
            results['error'] = str(e)
        
        return results
    
    def run(
        self,
        sites: List[str] = None,
        product_lines: List[str] = None,
        headless: bool = False,
        resume: bool = True
    ) -> Dict:
        """
        运行完整流程
        
        Args:
            sites: 站点列表
            product_lines: 产品线列表
            headless: 是否使用无头模式
            resume: 是否断点续传
            
        Returns:
            运行结果
        """
        logger.info("=" * 50)
        logger.info("开始竞品监控完整流程")
        logger.info("=" * 50)
        
        pipeline_results = {
            'pipeline': 'zhixia_monitor',
            'start_time': datetime.now().isoformat(),
            'stages': {},
        }
        
        # 阶段1: 采集
        logger.info("\n>>> 阶段1: 数据采集")
        collect_results = self.collect(
            sites=sites,
            product_lines=product_lines,
            headless=headless,
            resume=resume
        )
        pipeline_results['stages']['collect'] = collect_results
        
        if collect_results['status'] == 'error':
            pipeline_results['status'] = 'error'
            pipeline_results['error'] = '采集阶段失败'
            return pipeline_results
        
        # 阶段2: 处理
        if collect_results.get('files'):
            logger.info("\n>>> 阶段2: 数据处理")
            process_results = self.process()
            pipeline_results['stages']['process'] = process_results
        
        # 汇总
        pipeline_results['end_time'] = datetime.now().isoformat()
        pipeline_results['status'] = 'completed'
        
        # 打印摘要
        self._print_summary(pipeline_results)
        
        # 保存日志
        log_file = self._save_log('pipeline', pipeline_results)
        pipeline_results['log_file'] = log_file
        
        return pipeline_results
    
    def _print_summary(self, results: Dict):
        """打印摘要"""
        print("\n" + "=" * 50)
        print("竞品监控完成!")
        print("=" * 50)
        
        # 采集摘要
        collect = results.get('stages', {}).get('collect', {})
        print(f"采集: 成功 {collect.get('completed', 0)}, 失败 {collect.get('failed', 0)}")
        print(f"文件数: {len(collect.get('files', []))}")
        
        # 处理摘要
        process = results.get('stages', {}).get('process', {})
        if process.get('status') == 'completed':
            print(f"处理: {process.get('records', 0)} 条记录")
            print(f"CSV: {process.get('csv_file', 'N/A')}")
        
        print("=" * 50)
    
    def get_status(self) -> Dict:
        """获取状态"""
        status = {
            'system': 'ready',
            'scraper': None,
            'cookie': None,
        }
        
        try:
            if self._init_scraper():
                login_status = self.scraper.login_manager.get_status()
                status['scraper'] = 'initialized'
                status['cookie'] = login_status.get('cookie_status', {})
        except:
            status['scraper'] = 'error'
        
        return status
    
    def clear_cache(self):
        """清除缓存"""
        if self.scraper:
            self.scraper.clear_cache()
        logger.info("缓存已清除")


# ==================== 命令行入口 ====================

def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='知虾竞品监控 - 优化版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 登录检查
  python zhixia_monitor.py login
  
  # 采集数据（默认站点和关键词）
  python zhixia_monitor.py collect
  
  # 采集指定站点
  python zhixia_monitor.py collect --sites MY ID --product-lines OP
  
  # 完整流程
  python zhixia_monitor.py run --sites MY --product-lines OP
  
  # 不使用断点续传
  python zhixia_monitor.py run --no-resume
  
  # 查看状态
  python zhixia_monitor.py status
"""
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # login命令
    login_parser = subparsers.add_parser('login', help='登录')
    login_parser.add_argument('--force', action='store_true', help='强制重新登录')
    
    # collect命令
    collect_parser = subparsers.add_parser('collect', help='采集数据')
    collect_parser.add_argument('--sites', '-s', nargs='+', help='站点列表')
    collect_parser.add_argument('--product-lines', '-p', nargs='+', help='产品线列表')
    collect_parser.add_argument('--headless', action='store_true', help='无头模式')
    collect_parser.add_argument('--no-resume', action='store_true', help='不使用断点续传')
    
    # run命令
    run_parser = subparsers.add_parser('run', help='完整流程')
    run_parser.add_argument('--sites', '-s', nargs='+', help='站点列表')
    run_parser.add_argument('--product-lines', '-p', nargs='+', help='产品线列表')
    run_parser.add_argument('--headless', action='store_true', help='无头模式')
    run_parser.add_argument('--no-resume', action='store_true', help='不使用断点续传')
    
    # process命令
    subparsers.add_parser('process', help='处理数据')
    
    # status命令
    subparsers.add_parser('status', help='查看状态')
    
    # cache命令
    cache_parser = subparsers.add_parser('cache', help='清除缓存')
    
    args = parser.parse_args()
    
    # 默认命令
    if args.command is None:
        args.command = 'run'
    
    # 创建监控器
    monitor = ZhixiaMonitor()
    
    # 执行命令
    try:
        if args.command == 'login':
            result = monitor.login(force=args.force)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        elif args.command == 'collect':
            result = monitor.collect(
                sites=args.sites,
                product_lines=args.product_lines,
                headless=args.headless,
                resume=not args.no_resume
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        elif args.command == 'run':
            result = monitor.run(
                sites=args.sites,
                product_lines=args.product_lines,
                headless=args.headless,
                resume=not args.no_resume
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        elif args.command == 'process':
            result = monitor.process()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        elif args.command == 'status':
            status = monitor.get_status()
            print(json.dumps(status, ensure_ascii=False, indent=2))
            
        elif args.command == 'cache':
            monitor.clear_cache()
            print("缓存已清除")
            
    except KeyboardInterrupt:
        print("\n已取消")
        if monitor.scraper:
            monitor.scraper.close()


if __name__ == '__main__':
    main()
