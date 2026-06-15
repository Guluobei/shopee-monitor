#!/usr/bin/env python3
"""
知虾数据采集 - 每日运行入口
整合登录、采集、处理流程
"""

import os
import sys
import json
import yaml
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path

# 添加脚本目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from zhixia_scraper import ZhixiaScraper

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_daily(
    sites: list = None,
    product_lines: list = None,
    headless: bool = False,
    max_count: int = 500,
    output_dir: str = None
):
    """
    执行每日采集任务
    
    Args:
        sites: 站点列表，如 ['MY', 'ID', 'TH']
        product_lines: 产品线列表，如 ['OP', 'OM']
        headless: 是否无头模式
        max_count: 最大导出数量
        output_dir: 输出目录
    """
    logger.info("=" * 60)
    logger.info("Daily Data Collection Task")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    # 加载配置
    config_path = os.path.join(script_dir, '..', 'config', 'competitors.yaml')
    
    # 创建采集器
    scraper = ZhixiaScraper(config_path=config_path)
    
    # 设置输出目录
    if output_dir:
        scraper.download_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    # 执行采集
    results = scraper.run_scrape(
        sites=sites,
        product_lines=product_lines
    )
    
    # 保存结果
    results_dir = os.path.join(script_dir, '..', 'output')
    os.makedirs(results_dir, exist_ok=True)
    
    result_file = os.path.join(
        results_dir,
        f"daily_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
    )
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 打印摘要
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("Task Summary")
    print("=" * 60)
    print(f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Status: {results.get('status', 'unknown')}")
    print(f"Exports: {len(results.get('exports', []))}")
    print(f"Errors: {len(results.get('errors', []))}")
    print(f"Result file: {result_file}")
    print("=" * 60)
    
    # 列出导出的文件
    if results.get('exports'):
        print("\nExported files:")
        for f in results['exports']:
            print(f"  - {f}")
    
    return results


def run_test():
    """运行测试模式 - 只测试一个站点一个关键词"""
    logger.info("Running test mode...")
    
    return run_daily(
        sites=['MY'],  # 只测试马来西亚站点
        product_lines=['OP'],  # 只测试一个产品线
        headless=False,  # 可见模式便于观察
        max_count=10  # 只导出10条
    )


def run_full():
    """运行完整采集 - 所有站点所有产品线"""
    logger.info("Running full collection...")
    
    return run_daily(
        sites=None,  # 所有站点
        product_lines=None,  # 所有产品线
        headless=False,
        max_count=500
    )


def main():
    parser = argparse.ArgumentParser(
        description='知虾数据采集 - 每日运行工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 测试模式
  python run_daily.py test
  
  # 完整采集
  python run_daily.py full
  
  # 指定站点和产品线
  python run_daily.py run --sites MY ID --product-lines OP OM
  
  # 无头模式
  python run_daily.py run --sites MY --headless
"""
    )
    
    parser.add_argument(
        'mode',
        choices=['test', 'full', 'run'],
        default='run',
        help='运行模式: test(测试), full(完整), run(自定义)'
    )
    
    parser.add_argument('--sites', '-s', nargs='+',
                        help='站点列表，如 MY ID TH')
    parser.add_argument('--product-lines', '-p', nargs='+',
                        help='产品线列表，如 OP OM')
    parser.add_argument('--headless', action='store_true',
                        help='无头模式')
    parser.add_argument('--max-count', '-m', type=int, default=500,
                        help='最大导出数量')
    parser.add_argument('--output', '-o', default=None,
                        help='输出目录')
    
    args = parser.parse_args()
    
    if args.mode == 'test':
        results = run_test()
    elif args.mode == 'full':
        results = run_full()
    else:
        results = run_daily(
            sites=args.sites,
            product_lines=args.product_lines,
            headless=args.headless,
            max_count=args.max_count,
            output_dir=args.output
        )
    
    # 返回状态码
    if results.get('status') == 'completed':
        return 0
    elif results.get('status') == 'login_failed':
        return 1
    else:
        return 2


if __name__ == '__main__':
    sys.exit(main())