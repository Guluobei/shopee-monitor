#!/usr/bin/env python3
"""
知虾数据采集脚本 v3
基于 Playwright 的自动化采集工具
"""

import os
import sys
import json
import yaml
import time
import logging
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from playwright.sync_api import TimeoutError as PlaywrightTimeout

try:
    from zhixia_login import ZhixiaLoginManager
    LOGIN_MANAGER_AVAILABLE = True
except ImportError:
    LOGIN_MANAGER_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ZhixiaScraper:
    """知虾数据采集器 v3"""
    
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
        'CO': '哥伦比亚',
        'CL': '智利',
    }
    
    def __init__(self, config_path: str = None, use_login_manager: bool = True):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__),
                '..', 'config', 'competitors.yaml'
            )
        
        self.config = self._load_config(config_path)
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
        self.use_login_manager = use_login_manager and LOGIN_MANAGER_AVAILABLE
        
        if self.use_login_manager:
            logger.info("使用登录管理器")
            self.login_manager = ZhixiaLoginManager(
                config=self.config,
                cookie_file=os.path.join(os.path.dirname(__file__), '..', 'data', 'cookies.json'),
                screenshot_dir=os.path.join(os.path.dirname(__file__), '..', 'data', 'screenshots')
            )
        else:
            self.login_manager = None
        
        self.cookie_file = os.path.join(
            os.path.dirname(__file__),
            '..', 'data', 'cookies.json'
        )
        os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
        
        download_dir = os.path.abspath(self.config['browser']['download_dir'])
        os.makedirs(download_dir, exist_ok=True)
        self.download_dir = download_dir
    
    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def save_cookies(self) -> None:
        try:
            cookies = self.context.cookies()
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"Cookies saved: {self.cookie_file}")
        except Exception as e:
            logger.warning(f"Save cookies failed: {e}")
    
    def load_cookies(self) -> bool:
        if not os.path.exists(self.cookie_file):
            return False
        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            self.context.add_cookies(cookies)
            logger.info("Cookies loaded")
            return True
        except Exception as e:
            logger.warning(f"Load cookies failed: {e}")
            return False
    
    def launch_browser(self, headless: bool = None) -> bool:
        """启动浏览器并登录"""
        if headless is None:
            headless = self.config['browser'].get('headless', False)
        
        if self.use_login_manager and self.login_manager:
            logger.info("Using login manager...")
            success, status = self.login_manager.ensure_login(
                force_visible=not headless,
                auto_login_timeout=180
            )
            
            if success:
                self.browser = self.login_manager.get_browser()
                self.context = self.login_manager.get_context()
                self.page = self.login_manager.get_page()
                self.playwright = self.login_manager.playwright
                logger.info(f"Login success: {status}")
                return True
            
            logger.warning(f"Login failed: {status}")
            return False
        
        # 传统方式
        logger.info("Starting browser...")
        self.playwright = sync_playwright().start()
        
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )
        
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            accept_downloads=True,
        )
        
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
        """)
        
        self.page = self.context.new_page()
        logger.info("Browser started")
        
        self.load_cookies()
        
        # 检查登录状态
        self.page.goto(self.config['zhixia']['base_url'], wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)
        
        current_url = self.page.url.lower()
        if any(p in current_url for p in ['login', 'signin', 'passport', 'auth']):
            logger.warning("Not logged in")
            return False
        
        return True
    
    def close_browser(self) -> None:
        if self.use_login_manager and self.login_manager:
            self.login_manager.close_browser()
            self.browser = None
            self.context = None
            self.page = None
            self.playwright = None
            return
        
        if self.context:
            self.save_cookies()
        
        try:
            if self.browser:
                self.browser.close()
                self.playwright.stop()
                logger.info("Browser closed")
        except Exception as e:
            logger.warning(f"Close browser error: {e}")
    
    def select_site(self, site_code: str) -> bool:
        """切换站点 - 使用下拉菜单方式"""
        site_name = self.SITE_NAMES.get(site_code, site_code)
        logger.info(f"Switching to site: {site_code} ({site_name})")
        
        try:
            # 等待页面稳定
            time.sleep(2)
            
            # 查找站点选择器按钮（顶部显示当前站点）
            site_selectors = [
                'button:has-text("站点")',
                '[class*="site-selector"]',
                '[class*="siteSelect"]',
                'div:has-text("站点:")',
            ]
            
            site_btn = None
            for selector in site_selectors:
                try:
                    elements = self.page.query_selector_all(selector)
                    for el in elements:
                        if el.is_visible():
                            text = el.inner_text()
                            if '站点' in text or site_code in text:
                                site_btn = el
                                break
                    if site_btn:
                        break
                except:
                    continue
            
            if site_btn:
                site_btn.click()
                logger.info("Site selector clicked")
                time.sleep(1)
            else:
                # 尝试直接点击包含站点名称的元素
                logger.info("Trying direct site link...")
                try:
                    self.page.click(f'text={site_name}', timeout=3000)
                    time.sleep(2)
                    return True
                except:
                    pass
            
            # 在下拉菜单中点击目标站点
            try:
                self.page.click(f'text={site_name}', timeout=5000)
                logger.info(f"Site selected: {site_name}")
                time.sleep(3)
                
                # 验证切换成功
                self.page.wait_for_load_state('networkidle', timeout=10000)
                return True
            except Exception as e:
                logger.warning(f"Select site failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Site switch error: {e}")
            return False
    
    def go_to_search_page(self) -> bool:
        """进入搜索页面"""
        logger.info("Navigating to search page...")
        
        base_url = self.config['zhixia']['base_url']
        search_url = f"{base_url}/workbench/search/keyword-fuzzy-search?type=1&searchType=2"
        
        try:
            self.page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
            time.sleep(3)
            self.page.wait_for_load_state('networkidle', timeout=15000)
            logger.info("Search page loaded")
            return True
        except Exception as e:
            logger.error(f"Navigate to search failed: {e}")
            return False
    
    def search_keyword(self, keyword: str) -> bool:
        """搜索关键词"""
        logger.info(f"Searching: {keyword}")
        
        try:
            # 通过URL直接访问搜索结果
            base_url = self.config['zhixia']['base_url']
            encoded_kw = urllib.parse.quote(keyword)
            search_url = f"{base_url}/workbench/search/keyword-fuzzy-search?type=1&search={encoded_kw}&searchType=2"
            
            self.page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
            time.sleep(5)
            
            try:
                self.page.wait_for_load_state('networkidle', timeout=15000)
            except:
                pass
            
            # 检查是否有结果
            time.sleep(3)
            logger.info("Search results loaded")
            return True
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return False
    
    def export_data(self, filename: str = None, max_count: int = 500) -> Optional[str]:
        """导出数据"""
        logger.info("Exporting data...")
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"export_{timestamp}.xlsx"
        
        output_path = os.path.join(self.download_dir, filename)
        
        try:
            time.sleep(3)
            self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # 点击导出按钮
            export_clicked = False
            export_selectors = [
                'button:has-text("导出")',
                'button:has-text("导 出")',
                '[class*="export-btn"]',
            ]
            
            for selector in export_selectors:
                try:
                    btn = self.page.wait_for_selector(selector, timeout=3000)
                    if btn and btn.is_visible():
                        btn.click()
                        export_clicked = True
                        logger.info("Export button clicked")
                        break
                except:
                    continue
            
            if not export_clicked:
                logger.warning("Export button not found")
                return None
            
            time.sleep(2)
            
            # 填写导出范围
            try:
                inputs = self.page.query_selector_all('input[type="text"], input:not([type])')
                visible_inputs = [i for i in inputs if i.is_visible()]
                
                if len(visible_inputs) >= 2:
                    visible_inputs[0].fill('1')
                    time.sleep(0.5)
                    visible_inputs[1].fill(str(max_count))
                    logger.info(f"Export range: 1-{max_count}")
            except Exception as e:
                logger.warning(f"Fill range failed: {e}")
            
            time.sleep(1)
            
            # 点击确认
            confirm_selectors = [
                'button:has-text("确认导出")',
                'button:has-text("确定")',
                'button:has-text("确认")',
            ]
            
            for selector in confirm_selectors:
                try:
                    self.page.click(selector, timeout=3000)
                    logger.info("Confirm clicked")
                    break
                except:
                    continue
            
            # 等待下载
            logger.info("Waiting for download...")
            time.sleep(15)
            
            # 检查文件
            if os.path.exists(output_path):
                logger.info(f"File downloaded: {output_path}")
                return output_path
            
            # 检查下载目录中的新文件
            files = os.listdir(self.download_dir)
            xlsx_files = [f for f in files if f.endswith('.xlsx')]
            if xlsx_files:
                latest = max(xlsx_files, key=lambda f: os.path.getmtime(os.path.join(self.download_dir, f)))
                return os.path.join(self.download_dir, latest)
            
            logger.warning("No file downloaded")
            return None
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
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
            logged_in = self.launch_browser()
            
            if not logged_in:
                results['status'] = 'login_failed'
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
                            if not self.search_keyword(keyword):
                                task['status'] = 'search_failed'
                                results['errors'].append(task)
                                continue
                            
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
            self.close_browser()
        
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
    
    parser = argparse.ArgumentParser(description='知虾数据采集工具')
    parser.add_argument('--config', '-c', default=None)
    parser.add_argument('--sites', '-s', nargs='+')
    parser.add_argument('--product-lines', '-p', nargs='+')
    
    args = parser.parse_args()
    
    scraper = ZhixiaScraper(config_path=args.config)
    results = scraper.run_scrape(
        sites=args.sites,
        product_lines=args.product_lines
    )
    
    scraper.save_results(results)
    
    print(f"\nCompleted: {len(results['exports'])} exports")
    print(f"Errors: {len(results['errors'])}")


if __name__ == '__main__':
    main()