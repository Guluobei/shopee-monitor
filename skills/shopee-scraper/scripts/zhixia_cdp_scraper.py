#!/usr/bin/env python3
"""
知虾数据采集脚本 - CDP 版本
使用 web-access CDP Proxy 复用 Chrome 浏览器登录状态
无需独立启动浏览器，直接操作用户日常浏览器
"""

import os
import sys
import json
import yaml
import time
import logging
import urllib.parse
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CDPClient:
    """CDP Proxy 客户端"""
    
    PROXY_URL = "http://localhost:3456"
    
    def __init__(self):
        self.target_id = None
    
    def list_targets(self) -> List[Dict]:
        """列出所有打开的 tab"""
        resp = requests.get(f"{self.PROXY_URL}/targets")
        return resp.json()
    
    def new_tab(self, url: str) -> str:
        """创建新后台 tab"""
        resp = requests.post(
            f"{self.PROXY_URL}/new",
            data=url.encode('utf-8')
        )
        result = resp.json()
        self.target_id = result.get('targetId')
        logger.info(f"Created new tab: {self.target_id}")
        return self.target_id
    
    def navigate(self, url: str) -> bool:
        """导航到 URL"""
        if not self.target_id:
            return False
        resp = requests.post(
            f"{self.PROXY_URL}/navigate",
            params={'target': self.target_id},
            data=url.encode('utf-8')
        )
        return resp.status_code == 200
    
    def eval_js(self, script: str) -> any:
        """执行 JavaScript"""
        if not self.target_id:
            return None
        resp = requests.post(
            f"{self.PROXY_URL}/eval",
            params={'target': self.target_id},
            data=script.encode('utf-8')
        )
        try:
            return resp.json()
        except:
            return resp.text
    
    def click(self, selector: str) -> bool:
        """点击元素"""
        if not self.target_id:
            return False
        resp = requests.post(
            f"{self.PROXY_URL}/click",
            params={'target': self.target_id},
            data=selector.encode('utf-8')
        )
        return resp.status_code == 200
    
    def scroll(self, y: int = 3000, direction: str = None) -> bool:
        """滚动页面"""
        if not self.target_id:
            return False
        params = {'target': self.target_id}
        if direction:
            params['direction'] = direction
        else:
            params['y'] = y
        resp = requests.get(f"{self.PROXY_URL}/scroll", params=params)
        return resp.status_code == 200
    
    def screenshot(self, filepath: str) -> bool:
        """截图"""
        if not self.target_id:
            return False
        resp = requests.get(
            f"{self.PROXY_URL}/screenshot",
            params={'target': self.target_id, 'file': filepath}
        )
        return resp.status_code == 200
    
    def get_info(self) -> Dict:
        """获取页面信息"""
        if not self.target_id:
            return {}
        resp = requests.get(
            f"{self.PROXY_URL}/info",
            params={'target': self.target_id}
        )
        return resp.json()
    
    def close_tab(self) -> bool:
        """关闭 tab"""
        if not self.target_id:
            return False
        resp = requests.get(
            f"{self.PROXY_URL}/close",
            params={'target': self.target_id}
        )
        self.target_id = None
        return resp.status_code == 200


class ZhixiaCDPScraper:
    """知虾数据采集器 - CDP 版本"""
    
    # 站点名称映射
    SITE_NAMES = {
        'MY': '马来西亚',
        'ID': '印尼',
        'TH': '泰国',
        'PH': '菲律宾',
        'SG': '新加坡',
        'VN': '越南',
        'TW': '中国台湾',
        'BR': '巴西',
        'MX': '墨西哥',
    }
    
    BASE_URL = 'https://shopee.menglar.com'
    WORKBENCH_URL = 'https://shopee.menglar.com/workbench/home'
    SEARCH_URL = 'https://shopee.menglar.com/workbench/search/keyword-fuzzy-search'
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__),
                '..', 'config', 'competitors.yaml'
            )
        
        self.config = self._load_config(config_path)
        self.cdp = CDPClient()
        
        download_dir = os.path.abspath(self.config['browser']['download_dir'])
        os.makedirs(download_dir, exist_ok=True)
        self.download_dir = download_dir
    
    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def check_login(self) -> bool:
        """检查登录状态"""
        # 获取当前 URL
        info = self.cdp.get_info()
        url = info.get('url', '').lower()
        
        # 检查是否在登录页
        login_patterns = ['/login', 'signin', 'passport', 'auth']
        for pattern in login_patterns:
            if pattern in url:
                return False
        
        # 检查是否在工作台
        if 'workbench' in url and '/login' not in url:
            return True
        
        # 检查页面元素
        result = self.cdp.eval_js("""
            (() => {
                const userIndicators = document.querySelectorAll('[class*="user"], [class*="avatar"], [class*="account"]');
                const renewBtn = document.body.innerText.includes('我要续费');
                const navCenter = document.body.innerText.includes('监控中心');
                return {
                    hasUserElements: userIndicators.length > 0,
                    hasRenewBtn: renewBtn,
                    hasNavCenter: navCenter
                };
            })()
        """)
        
        if result and (result.get('hasRenewBtn') or result.get('hasNavCenter')):
            return True
        
        return False
    
    def open_workbench(self) -> bool:
        """打开工作台"""
        logger.info("Opening workbench...")
        
        # 创建新 tab
        self.cdp.new_tab(self.WORKBENCH_URL)
        time.sleep(3)
        
        # 检查登录状态
        if not self.check_login():
            logger.warning("Not logged in")
            return False
        
        logger.info("Logged in successfully")
        return True
    
    def select_site(self, site_code: str) -> bool:
        """切换站点"""
        site_name = self.SITE_NAMES.get(site_code, site_code)
        logger.info(f"Switching to site: {site_code} ({site_name})")
        
        # 等待页面稳定
        time.sleep(2)
        
        # 尝试点击站点选择器
        result = self.cdp.eval_js("""
            (() => {
                // 查找站点按钮
                const buttons = document.querySelectorAll('button, div[role="button"]');
                for (const btn of buttons) {
                    if (btn.innerText.includes('站点')) {
                        btn.click();
                        return 'clicked_site_btn';
                    }
                }
                return 'no_site_btn';
            })()
        """)
        
        if result == 'clicked_site_btn':
            time.sleep(1)
            
            # 点击目标站点
            self.cdp.eval_js(f"""
                (() => {
                    const items = document.querySelectorAll('div, span, a');
                    for (const item of items) {
                        if (item.innerText.includes('{site_name}')) {
                            item.click();
                            return 'clicked_site';
                        }
                    }
                    return 'no_site_item';
                })()
            """)
            
            time.sleep(3)
            logger.info(f"Site selected: {site_name}")
            return True
        
        return False
    
    def search_keyword(self, keyword: str) -> bool:
        """搜索关键词"""
        logger.info(f"Searching: {keyword}")
        
        encoded_kw = urllib.parse.quote(keyword)
        search_url = f"{self.SEARCH_URL}?type=1&search={encoded_kw}&searchType=2"
        
        self.cdp.navigate(search_url)
        time.sleep(5)
        
        # 检查是否有结果
        result = self.cdp.eval_js("""
            (() => {
                const tables = document.querySelectorAll('table, [class*="table"]');
                const results = document.querySelectorAll('[class*="result"], [class*="item"]');
                return {
                    hasTable: tables.length > 0,
                    hasResults: results.length > 0,
                    bodyText: document.body.innerText.substring(0, 500)
                };
            })()
        """)
        
        if result and (result.get('hasTable') or result.get('hasResults')):
            logger.info("Search results found")
            return True
        
        logger.warning("No search results")
        return True  # 继续尝试导出
    
    def export_data(self, filename: str = None, max_count: int = 500) -> Optional[str]:
        """导出数据"""
        logger.info("Exporting data...")
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"export_{timestamp}.xlsx"
        
        # 等待页面稳定
        time.sleep(3)
        
        # 点击导出按钮
        result = self.cdp.eval_js("""
            (() => {
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.innerText.includes('导出')) {
                        btn.click();
                        return 'clicked_export';
                    }
                }
                return 'no_export_btn';
            })()
        """)
        
        if result != 'clicked_export':
            logger.warning("Export button not found")
            return None
        
        logger.info("Export button clicked")
        time.sleep(2)
        
        # 填写导出范围
        self.cdp.eval_js(f"""
            (() => {
                const inputs = document.querySelectorAll('input[type="text"], input:not([type])');
                if (inputs.length >= 2) {
                    inputs[0].value = '1';
                    inputs[1].value = '{max_count}';
                }
            })()
        """)
        
        time.sleep(1)
        
        # 点击确认导出
        self.cdp.eval_js("""
            (() => {
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.innerText.includes('确认导出') || btn.innerText.includes('确定')) {
                        btn.click();
                        return 'clicked_confirm';
                    }
                }
                return 'no_confirm_btn';
            })()
        """)
        
        logger.info("Confirm clicked, waiting for download...")
        time.sleep(15)
        
        # 检查下载目录
        files = os.listdir(self.download_dir)
        xlsx_files = [f for f in files if f.endswith('.xlsx')]
        
        if xlsx_files:
            latest = max(xlsx_files, key=lambda f: os.path.getmtime(os.path.join(self.download_dir, f)))
            filepath = os.path.join(self.download_dir, latest)
            logger.info(f"File downloaded: {filepath}")
            return filepath
        
        logger.warning("No file downloaded")
        return None
    
    def run_scrape(
        self,
        sites: List[str] = None,
        product_lines: List[str] = None,
    ) -> Dict:
        """执行采集任务"""
        results = {
            'start_time': datetime.now().isoformat(),
            'tasks': [],
            'exports': [],
            'errors': []
        }
        
        if sites is None:
            sites = [s['code'] for s in self.config['sites']]
        
        if product_lines is None:
            product_lines = list(self.config['product_lines'].keys())
        
        try:
            # 打开工作台（复用 Chrome 登录状态）
            if not self.open_workbench():
                results['status'] = 'login_failed'
                results['message'] = '请在 Chrome 浏览器中登录知虾网站后重试'
                return results
            
            for site_code in sites:
                logger.info(f"\n{'='*50}")
                logger.info(f"Processing site: {site_code}")
                logger.info(f"{'='*50}")
                
                # 切换站点
                self.select_site(site_code)
                time.sleep(2)
                
                for pl_code in product_lines:
                    pl_info = self.config['product_lines'].get(pl_code)
                    if not pl_info:
                        continue
                    
                    logger.info(f"Product line: {pl_info['name']}")
                    
                    for keyword in pl_info['keywords']:
                        task = {
                            'site': site_code,
                            'product_line': pl_code,
                            'keyword': keyword,
                            'timestamp': datetime.now().isoformat(),
                        }
                        
                        try:
                            # 搜索
                            self.search_keyword(keyword)
                            time.sleep(3)
                            
                            # 导出
                            filename = f"{site_code}_{pl_code}_{keyword.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                            export_path = self.export_data(filename)
                            
                            if export_path:
                                task['status'] = 'success'
                                task['file'] = export_path
                                results['exports'].append(export_path)
                                logger.info(f"Exported: {filename}")
                            else:
                                task['status'] = 'export_failed'
                                results['errors'].append(task)
                            
                        except Exception as e:
                            task['status'] = 'error'
                            task['error'] = str(e)
                            results['errors'].append(task)
                            logger.error(f"Task error: {e}")
                        
                        results['tasks'].append(task)
                        time.sleep(3)
            
            results['end_time'] = datetime.now().isoformat()
            results['status'] = 'completed'
            
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            logger.error(f"Scrape error: {e}")
        
        finally:
            # 关闭创建的 tab
            self.cdp.close_tab()
        
        return results
    
    def save_results(self, results: Dict, output_path: str = None) -> None:
        if output_path is None:
            output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(
                output_dir,
                f"scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Results saved: {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='知虾数据采集工具 (CDP版本)')
    parser.add_argument('--config', '-c', default=None)
    parser.add_argument('--sites', '-s', nargs='+')
    parser.add_argument('--product-lines', '-p', nargs='+')
    
    args = parser.parse_args()
    
    scraper = ZhixiaCDPScraper(config_path=args.config)
    results = scraper.run_scrape(
        sites=args.sites,
        product_lines=args.product_lines
    )
    
    scraper.save_results(results)
    
    print(f"\nCompleted: {len(results['exports'])} exports")
    print(f"Errors: {len(results['errors'])}")
    
    if results.get('status') == 'login_failed':
        print(f"\n提示: {results.get('message')}")


if __name__ == '__main__':
    main()