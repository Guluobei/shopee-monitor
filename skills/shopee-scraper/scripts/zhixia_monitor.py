#!/usr/bin/env python3
"""
知虾竞品监控系统 - 主程序
整合浏览器采集和数据处理，实现完整的竞品监控流程
"""

import os
import sys
import json
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from zhixia_scraper import ZhixiaScraper
from data_processor import DataProcessor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ZhixiaMonitor:
    """知虾竞品监控器"""

    def __init__(self, config_path: str = None, skill_dir: str = None):
        """
        初始化监控器

        Args:
            config_path: 配置文件路径
            skill_dir: Skill目录路径（用于加载配置和输出）
        """
        if skill_dir is None:
            # 默认使用当前目录的父级目录
            skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if config_path is None:
            config_path = os.path.join(skill_dir, 'config', 'competitors.yaml')

        self.skill_dir = Path(skill_dir)
        self.config = self._load_config(config_path)
        self.config_path = config_path

        # 初始化组件
        self.scraper = ZhixiaScraper(config_path=config_path)
        self.processor = DataProcessor(config_path=config_path)

        # 输出目录
        self.output_dir = self.skill_dir / 'output'
        self.output_dir.mkdir(exist_ok=True)

        # 记录文件
        self.log_dir = self.skill_dir / 'logs'
        self.log_dir.mkdir(exist_ok=True)

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _save_log(self, task_type: str, data: Dict) -> str:
        """保存任务日志"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.log_dir / f'{task_type}_{timestamp}.json'

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(log_file)

    def collect(
        self,
        sites: List[str] = None,
        product_lines: List[str] = None,
        keywords: List[str] = None,
        headless: bool = False
    ) -> Dict:
        """
        采集数据

        Args:
            sites: 指定站点列表，如 ['MY', 'ID']
            product_lines: 指定产品线，如 ['OP', 'OM']
            keywords: 指定关键词（覆盖产品线配置）
            headless: 是否使用无头模式

        Returns:
            采集结果
        """
        logger.info("="*60)
        logger.info("开始竞品数据采集")
        logger.info("="*60)

        results = {
            'task': 'collect',
            'start_time': datetime.now().isoformat(),
            'config': {
                'sites': sites or 'all',
                'product_lines': product_lines or 'all',
                'keywords': keywords or 'from_config',
                'headless': headless
            },
            'status': 'pending',
            'downloads': []
        }

        try:
            # 临时修改headless配置
            if headless:
                self.scraper.config['browser']['headless'] = True

            # 执行采集
            scrape_results = self.scraper.run_scrape(
                sites=sites,
                product_lines=product_lines
            )

            results.update(scrape_results)

            # 获取下载的文件列表
            download_dir = self.scraper.config['browser']['download_dir']
            files = self.processor.find_downloaded_files(download_dir)

            # 只保留今天的文件
            today = datetime.now().strftime('%Y%m%d')
            results['downloads'] = [
                f for f in files
                if today in os.path.basename(f)
            ]

            results['status'] = 'completed'

            # 保存日志
            log_file = self._save_log('collect', results)
            results['log_file'] = log_file

            logger.info(f"采集完成，下载了 {len(results['downloads'])} 个文件")

        except Exception as e:
            logger.error(f"采集失败: {e}")
            results['status'] = 'error'
            results['error'] = str(e)

        finally:
            self.scraper.close_browser()

        return results

    def process(
        self,
        download_dir: str = None,
        output_dir: str = None,
        export_format: str = 'csv'
    ) -> Dict:
        """
        处理数据

        Args:
            download_dir: 下载目录（默认使用配置中的目录）
            output_dir: 输出目录
            export_format: 导出格式，支持 'csv', 'excel', 'both'

        Returns:
            处理结果
        """
        logger.info("="*60)
        logger.info("开始数据处理")
        logger.info("="*60)

        results = {
            'task': 'process',
            'start_time': datetime.now().isoformat(),
            'status': 'pending',
            'output_files': []
        }

        try:
            # 确定下载目录
            if download_dir is None:
                # 使用scraper配置中的下载目录
                scraper_config_path = os.path.join(
                    os.path.dirname(self.scraper.config.get('browser', {}).get('download_dir', './data/downloads')),
                    '..', 'config', 'competitors.yaml'
                )
                # 直接使用配置的下载目录
                download_dir = self.scraper.config['browser']['download_dir']

            # 确定输出目录
            if output_dir is None:
                output_dir = str(self.output_dir)

            # 执行处理
            process_results = self.processor.run_process(
                download_dir=download_dir,
                output_dir=output_dir,
                export_all=True
            )

            results.update(process_results)

            # 根据导出格式处理
            if export_format in ['csv', 'both']:
                if process_results.get('files', {}).get('csv'):
                    results['output_files'].append(
                        process_results['files']['csv']
                    )

            results['status'] = 'completed'

            # 保存日志
            log_file = self._save_log('process', results)
            results['log_file'] = log_file

            logger.info(f"处理完成，输出了 {len(results['output_files'])} 个文件")

        except Exception as e:
            logger.error(f"处理失败: {e}")
            results['status'] = 'error'
            results['error'] = str(e)

        return results

    def run_full_pipeline(
        self,
        sites: List[str] = None,
        product_lines: List[str] = None,
        headless: bool = False,
        export_format: str = 'csv'
    ) -> Dict:
        """
        运行完整流程：采集 -> 处理 -> 输出

        Args:
            sites: 指定站点
            product_lines: 指定产品线
            headless: 无头模式
            export_format: 导出格式

        Returns:
            完整流程结果
        """
        logger.info("="*60)
        logger.info("开始竞品监控完整流程")
        logger.info("="*60)

        pipeline_results = {
            'pipeline': 'zhixia_monitor',
            'start_time': datetime.now().isoformat(),
            'stages': {},
            'status': 'pending'
        }

        try:
            # 阶段1: 采集
            logger.info("\n>>> 阶段1: 数据采集")
            collect_results = self.collect(
                sites=sites,
                product_lines=product_lines,
                headless=headless
            )
            pipeline_results['stages']['collect'] = collect_results

            if collect_results['status'] != 'completed':
                logger.warning("采集阶段未完成，跳过后续处理")
                pipeline_results['status'] = 'collect_failed'
                return pipeline_results

            # 阶段2: 数据处理
            logger.info("\n>>> 阶段2: 数据处理")
            process_results = self.process()
            pipeline_results['stages']['process'] = process_results

            if process_results['status'] != 'completed':
                logger.warning("处理阶段未完成")
                pipeline_results['status'] = 'process_failed'
                return pipeline_results

            # 汇总结果
            pipeline_results['status'] = 'completed'
            pipeline_results['end_time'] = datetime.now().isoformat()
            pipeline_results['summary'] = {
                'total_downloads': len(collect_results.get('downloads', [])),
                'total_records': process_results.get('stats', {}).get('total_records', 0),
                'output_files': process_results.get('output_files', []),
            }

            # 保存完整日志
            log_file = self._save_log('pipeline', pipeline_results)
            pipeline_results['log_file'] = log_file

            # 打印摘要
            self._print_summary(pipeline_results['summary'])

        except Exception as e:
            logger.error(f"流程执行失败: {e}")
            pipeline_results['status'] = 'error'
            pipeline_results['error'] = str(e)

        return pipeline_results

    def _print_summary(self, summary: Dict) -> None:
        """打印结果摘要"""
        print("\n" + "="*60)
        print("竞品监控完成!")
        print("="*60)
        print(f"下载文件数: {summary.get('total_downloads', 0)}")
        print(f"处理记录数: {summary.get('total_records', 0)}")
        print(f"\n输出文件:")
        for f in summary.get('output_files', []):
            print(f"  - {f}")
        print("="*60)

    def get_status(self) -> Dict:
        """获取系统状态"""
        download_dir = self.scraper.config['browser']['download_dir']
        files = self.processor.find_downloaded_files(download_dir)

        today = datetime.now().strftime('%Y%m%d')
        today_files = [f for f in files if today in os.path.basename(f)]

        return {
            'status': 'ready',
            'download_dir': download_dir,
            'output_dir': str(self.output_dir),
            'total_files': len(files),
            'today_files': len(today_files),
            'config': {
                'sites': [s['code'] for s in self.config['sites']],
                'product_lines': list(self.config['product_lines'].keys()),
            }
        }

    def clean_downloads(self, days: int = 7) -> int:
        """
        清理旧的下载文件

        Args:
            days: 保留最近N天的文件

        Returns:
            清理的文件数量
        """
        import time

        download_dir = self.scraper.config['browser']['download_dir']
        files = self.processor.find_downloaded_files(download_dir)

        cutoff_time = time.time() - (days * 24 * 3600)
        removed = 0

        for filepath in files:
            if os.path.getmtime(filepath) < cutoff_time:
                try:
                    os.remove(filepath)
                    removed += 1
                    logger.info(f"已删除: {filepath}")
                except Exception as e:
                    logger.warning(f"删除失败 {filepath}: {e}")

        return removed


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='知虾竞品监控工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 运行完整流程（采集+处理）
  python zhixia_monitor.py run --sites MY ID --product-lines OP

  # 仅采集数据
  python zhixia_monitor.py collect --sites MY --headless

  # 仅处理数据
  python zhixia_monitor.py process

  # 查看状态
  python zhixia_monitor.py status

  # 清理7天前的下载文件
  python zhixia_monitor.py clean --days 7
"""
    )

    parser.add_argument(
        '--config', '-c',
        default=None,
        help='配置文件路径'
    )
    parser.add_argument(
        '--skill-dir', '-s',
        default=None,
        help='Skill目录路径'
    )

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # run命令 - 运行完整流程
    run_parser = subparsers.add_parser('run', help='运行完整流程')
    run_parser.add_argument('--sites', '-t', nargs='+',
                             help='指定站点，如 MY ID TH')
    run_parser.add_argument('--product-lines', '-p', nargs='+',
                            help='指定产品线，如 OP OM MIC_400_1000')
    run_parser.add_argument('--headless', action='store_true',
                            help='使用无头模式')
    run_parser.add_argument('--format', '-f', default='csv',
                            choices=['csv', 'excel', 'both'],
                            help='导出格式')

    # collect命令 - 仅采集
    collect_parser = subparsers.add_parser('collect', help='仅采集数据')
    collect_parser.add_argument('--sites', '-t', nargs='+',
                                help='指定站点')
    collect_parser.add_argument('--product-lines', '-p', nargs='+',
                                help='指定产品线')
    collect_parser.add_argument('--headless', action='store_true',
                               help='使用无头模式')

    # process命令 - 仅处理
    process_parser = subparsers.add_parser('process', help='仅处理数据')
    process_parser.add_argument('--download-dir', '-d', default=None,
                                help='下载目录')
    process_parser.add_argument('--output-dir', '-o', default=None,
                               help='输出目录')
    process_parser.add_argument('--format', '-f', default='csv',
                                choices=['csv', 'excel', 'both'],
                                help='导出格式')

    # status命令 - 查看状态
    subparsers.add_parser('status', help='查看系统状态')

    # clean命令 - 清理文件
    clean_parser = subparsers.add_parser('clean', help='清理旧文件')
    clean_parser.add_argument('--days', '-d', type=int, default=7,
                             help='保留天数（默认7天）')

    args = parser.parse_args()

    # 如果没有子命令，显示帮助
    if args.command is None:
        parser.print_help()
        return

    # 创建监控器
    monitor = ZhixiaMonitor(
        config_path=args.config,
        skill_dir=args.skill_dir
    )

    # 执行命令
    if args.command == 'run':
        results = monitor.run_full_pipeline(
            sites=args.sites,
            product_lines=args.product_lines,
            headless=args.headless,
            export_format=args.format
        )
        print(json.dumps(results, ensure_ascii=False, indent=2))

    elif args.command == 'collect':
        results = monitor.collect(
            sites=args.sites,
            product_lines=args.product_lines,
            headless=args.headless
        )
        print(json.dumps(results, ensure_ascii=False, indent=2))

    elif args.command == 'process':
        results = monitor.process(
            download_dir=args.download_dir,
            output_dir=args.output_dir,
            export_format=args.format
        )
        print(json.dumps(results, ensure_ascii=False, indent=2))

    elif args.command == 'status':
        status = monitor.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))

    elif args.command == 'clean':
        removed = monitor.clean_downloads(days=args.days)
        print(f"已清理 {removed} 个文件")


if __name__ == '__main__':
    main()
