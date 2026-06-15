#!/usr/bin/env python3
"""
知虾数据采集 - 每日运行入口
支持两种模式：
1. CDP 模式：复用 Chrome 浏览器登录状态（推荐）
2. Playwright 模式：独立启动浏览器
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

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_daily_cdp(
    sites: list = None,
    product_lines: list = None,
    max_count: int = 500,
    output_dir: str = None
):
    """使用 CDP 模式采集（复用 Chrome 登录状态）"""
    logger.info("=" * 60)
    logger.info("Daily Data Collection - CDP Mode")
    logger.info("=" * 60)
    
    from zhixia_cdp_scraper import ZhixiaCDPScraper
    
    config_path = os.path.join(script_dir, '..', 'config', 'competitors.yaml')
    scraper = ZhixiaCDPScraper(config_path=config_path)
    
    if output_dir:
        scraper.download_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    start_time = datetime.now()
    results = scraper.run_scrape(
        sites=sites,
        product_lines=product_lines
    )
    
    # 保存结果
    results_dir = os.path.join(script_dir, '..', 'output')
    os.makedirs(results_dir, exist_ok=True)
    
    result_file = os.path.join(
        results_dir,
        f"daily_cdp_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
    )
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 打印摘要
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("Task Summary (CDP Mode)")
    print("=" * 60)
    print(f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Status: {results.get('status', 'unknown')}")
    print(f"Exports: {len(results.get('exports', []))}")
    print(f"Errors: {len(results.get('errors', []))}")
    
    if results.get('status') == 'login_failed':
        print(f"\n提示: {results.get('message')}")
    
    print("=" * 60)
    
    return results


def run_daily_playwright(
    sites: list = None,
    product_lines: list = None,
    headless: bool = False,
    max_count: int = 500,
    output_dir: str = None
):
    """使用 Playwright 模式采集（独立浏览器）"""
    logger.info("=" * 60)
    logger.info("Daily Data Collection - Playwright Mode")
    logger.info("=" * 60)
    
    from zhixia_scraper import ZhixiaScraper
    
    config_path = os.path.join(script_dir, '..', 'config', 'competitors.yaml')
    scraper = ZhixiaScraper(config_path=config_path)
    
    if output_dir:
        scraper.download_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    start_time = datetime.now()
    results = scraper.run_scrape(
        sites=sites,
        product_lines=product_lines
    )
    
    # 保存结果
    results_dir = os.path.join(script_dir, '..', 'output')
    os.makedirs(results_dir, exist_ok=True)
    
    result_file = os.path.join(
        results_dir,
        f"daily_pw_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
    )
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # 打印摘要
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("Task Summary (Playwright Mode)")
    print("=" * 60)
    print(f"Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Status: {results.get('status', 'unknown')}")
    print(f"Exports: {len(results.get('exports', []))}")
    print(f"Errors: {len(results.get('errors', []))}")
    print("=" * 60)
    
    return results


def check_cdp_ready() -> bool:
    """检查 CDP Proxy 是否就绪"""
    import requests
    try:
        resp = requests.get("http://localhost:3456/targets", timeout=5)
        return resp.status_code == 200
    except:
        return False


def main():
    parser = argparse.ArgumentParser(
        description='知虾数据采集 - 每日运行工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # CDP 模式（推荐，复用 Chrome 登录状态）
  python run_daily.py cdp --sites MY ID --product-lines OP
  
  # Playwright 模式（独立浏览器）
  python run_daily.py pw --sites MY --headless
  
  # 测试模式（CDP，单站点）
  python run_daily.py test
  
  # 检查 CDP 状态
  python run_daily.py check
"""
    )
    
    parser.add_argument(
        'mode',
        choices=['cdp', 'pw', 'test', 'check'],
        default='cdp',
        help='运行模式: cdp(CDP模式), pw(Playwright模式), test(测试), check(检查CDP)'
    )
    
    parser.add_argument('--sites', '-s', nargs='+',
                        help='站点列表，如 MY ID TH')
    parser.add_argument('--product-lines', '-p', nargs='+',
                        help='产品线列表，如 OP OM')
    parser.add_argument('--headless', action='store_true',
                        help='Playwright 无头模式')
    parser.add_argument('--max-count', '-m', type=int, default=500,
                        help='最大导出数量')
    parser.add_argument('--output', '-o', default=None,
                        help='输出目录')
    
    args = parser.parse_args()
    
    if args.mode == 'check':
        ready = check_cdp_ready()
        if ready:
            print("CDP Proxy is ready")
            print("Chrome browser is connected")
        else:
            print("CDP Proxy is NOT ready")
            print("Please run: node check-deps.mjs")
        return 0
    
    if args.mode == 'test':
        # 测试模式：CDP，单站点单产品线
        results = run_daily_cdp(
            sites=['MY'],
            product_lines=['OP'],
            max_count=10
        )
        return 0 if results.get('status') == 'completed' else 1
    
    if args.mode == 'cdp':
        # 检查 CDP 是否就绪
        if not check_cdp_ready():
            print("CDP Proxy is NOT ready")
            print("Please ensure Chrome is running with remote debugging enabled")
            print("Run: node check-deps.mjs")
            return 1
        
        results = run_daily_cdp(
            sites=args.sites,
            product_lines=args.product_lines,
            max_count=args.max_count,
            output_dir=args.output
        )
        
        if results.get('status') == 'completed':
            return 0
        elif results.get('status') == 'login_failed':
            return 1
        else:
            return 2
    
    if args.mode == 'pw':
        results = run_daily_playwright(
            sites=args.sites,
            product_lines=args.product_lines,
            headless=args.headless,
            max_count=args.max_count,
            output_dir=args.output
        )
        
        if results.get('status') == 'completed':
            return 0
        elif results.get('status') == 'login_failed':
            return 1
        else:
            return 2


if __name__ == '__main__':
    sys.exit(main())