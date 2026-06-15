#!/usr/bin/env python3
"""
知虾数据采集脚本 - CDP 版本 v2
使用 web-access CDP Proxy 复用 Chrome 浏览器登录状态
无需独立启动浏览器，直接操作用户日常浏览器

v2 改进:
- 批次导出：自动分批导出超过100条的数据
- 结果计数：自动获取搜索结果总数
- 下载监控：等待下载完成并检测新文件
- URL检测：确保操作在预期页面
- 断点续传：支持进度保存和恢复
- 输入优化：使用 JS 设置值并触发 input 事件
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
from typing import Dict, List, Optional, Tuple

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
    """知虾数据采集器 - CDP 版本 v2"""
    
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
    
    # 导出批次大小限制（知虾平台限制）
    EXPORT_BATCH_SIZE = 100
    EXPORT_WAIT_TIME = 15  # 每批次导出等待时间
    
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
        
        # 进度文件路径
        self.progress_file = os.path.join(self.download_dir, '.scrape_progress.json')
    
    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _load_progress(self) -> Dict:
        """加载进度文件"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_progress(self, progress: Dict) -> None:
        """保存进度"""
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
    
    def _clear_progress(self) -> None:
        """清除进度"""
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)
    
    def check_login(self) -> bool:
        """检查登录状态"""
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
    
    def _ensure_on_page(self, expected_pattern: str) -> bool:
        """确保在预期页面"""
        info = self.cdp.get_info()
        current_url = info.get('url', '')
        
        if expected_pattern not in current_url:
            logger.warning(f"Unexpected URL: {current_url}, expected: {expected_pattern}")
            return False
        return True
    
    def open_workbench(self) -> bool:
        """打开工作台"""
        logger.info("Opening workbench...")
        
        self.cdp.new_tab(self.WORKBENCH_URL)
        time.sleep(3)
        
        if not self.check_login():
            logger.warning("Not logged in")
            return False
        
        logger.info("Logged in successfully")
        return True
    
    def select_site(self, site_code: str) -> bool:
        """切换站点"""
        site_name = self.SITE_NAMES.get(site_code, site_code)
        logger.info(f"Switching to site: {site_code} ({site_name})")
        
        time.sleep(2)
        
        result = self.cdp.eval_js("""
            (() => {
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
        
        return True
    
    def get_result_count(self) -> int:
        """获取搜索结果总数"""
        result = self.cdp.eval_js("""
            (() => {
                // 方法1: 从页面文本中查找总数
                const bodyText = document.body.innerText;
                const patterns = [
                    /共\s*(\d+)\s*条/,
                    /共\s*(\d+)\s*个/,
                    /(\d+)\s*条结果/,
                    /total\s*(\d+)/i
                ];
                
                for (const pattern of patterns) {
                    const match = bodyText.match(pattern);
                    if (match) {
                        return parseInt(match[1]);
                    }
                }
                
                // 方法2: 从分页信息计算
                const pagination = document.querySelector('[class*="pagination"]');
                if (pagination) {
                    const pageLinks = pagination.querySelectorAll('a, button, span');
                    let maxPage = 0;
                    for (const link of pageLinks) {
                        const num = parseInt(link.innerText);
                        if (num > maxPage) maxPage = num;
                    }
                    if (maxPage > 0) {
                        // 假设每页10条
                        return maxPage * 10;
                    }
                }
                
                // 方法3: 统计当前页面产品数量
                const productItems = document.querySelectorAll('[class*="product"], [class*="item"]');
                if (productItems.length > 0) {
                    return productItems.length;
                }
                
                return 0;
            })()
        """)
        
        count = result if isinstance(result, int) else 0
        logger.info(f"Result count: {count}")
        return count
    
    def _wait_for_download(self, timeout: int = 30) -> Optional[str]:
        """等待下载完成并返回新文件路径"""
        initial_files = set(os.listdir(self.download_dir))
        # 过滤掉临时下载文件
        initial_complete = {f for f in initial_files if not f.endswith('.crdownload') and not f.endswith('.tmp')}
        
        logger.info("Waiting for download...")
        
        for i in range(timeout):
            time.sleep(1)
            current_files = set(os.listdir(self.download_dir))
            current_complete = {f for f in current_files if not f.endswith('.crdownload') and not f.endswith('.tmp')}
            
            new_files = current_complete - initial_complete
            xlsx_new = [f for f in new_files if f.endswith('.xlsx')]
            
            if xlsx_new:
                # 等待文件写入完成
                time.sleep(2)
                filepath = os.path.join(self.download_dir, xlsx_new[0])
                logger.info(f"Downloaded: {filepath}")
                return filepath
        
        logger.warning("Download timeout")
        return None
    
    def _set_export_range(self, start: int, end: int) -> bool:
        """设置导出范围（使用 JS 触发 input 事件）"""
        result = self.cdp.eval_js(f"""
            (() => {
                // 查找导出弹窗中的输入框
                const inputs = document.querySelectorAll('input[type="text"], input:not([type])');
                
                // 筛选导出范围输入框（通常有两个相邻的输入框）
                let minInput = null;
                let maxInput = null;
                
                for (const input of inputs) {
                    const placeholder = input.placeholder || '';
                    const value = input.value || '';
                    
                    // 检查是否是序号输入框
                    if (placeholder.includes('输入') || placeholder.includes('序号') || 
                        value === '' || /^\d+$/.test(value)) {
                        if (!minInput) {
                            minInput = input;
                        } else if (!maxInput) {
                            maxInput = input;
                            break;
                        }
                    }
                }
                
                if (minInput && maxInput) {
                    // 清空并设置新值，触发 input 事件确保 Vue/React 感知
                    minInput.value = '{start}';
                    minInput.dispatchEvent(new Event('input', { bubbles: true }));
                    minInput.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    maxInput.value = '{end}';
                    maxInput.dispatchEvent(new Event('input', { bubbles: true }));
                    maxInput.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    return { success: true, start: {start}, end: {end} };
                }
                
                return { success: false, reason: 'inputs_not_found' };
            })()
        """)
        
        if result and result.get('success'):
            logger.info(f"Set export range: {start} - {end}")
            return True
        
        logger.warning(f"Failed to set export range: {result}")
        return False
    
    def _click_export_button(self) -> bool:
        """点击导出按钮"""
        result = self.cdp.eval_js("""
            (() => {
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.innerText.includes('导出') && !btn.innerText.includes('确认')) {
                        btn.click();
                        return 'clicked_export';
                    }
                }
                return 'no_export_btn';
            })()
        """)
        
        return result == 'clicked_export'
    
    def _click_confirm_export(self) -> bool:
        """点击确认导出按钮"""
        result = self.cdp.eval_js("""
            (() => {
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.innerText.includes('确认导出') || btn.innerText.includes('确定')) {
                        // 检查按钮是否可点击
                        if (!btn.disabled) {
                            btn.click();
                            return 'clicked_confirm';
                        }
                        return 'button_disabled';
                    }
                }
                return 'no_confirm_btn';
            })()
        """)
        
        if result == 'clicked_confirm':
            logger.info("Confirm export clicked")
            return True
        elif result == 'button_disabled':
            logger.info("Export button disabled (processing)")
            return False
        else:
            logger.warning("Confirm button not found")
            return False
    
    def _close_export_modal(self) -> bool:
        """关闭导出弹窗"""
        result = self.cdp.eval_js("""
            (() => {
                // 查找关闭按钮
                const closeButtons = document.querySelectorAll('[class*="close"], [aria-label*="close"], button');
                for (const btn of closeButtons) {
                    if (btn.innerText.includes('关闭') || btn.getAttribute('aria-label')?.includes('close')) {
                        btn.click();
                        return 'closed';
                    }
                }
                
                // 点击弹窗外部关闭
                const modal = document.querySelector('[class*="modal"], [class*="dialog"]');
                if (modal) {
                    const overlay = modal.parentElement;
                    if (overlay) {
                        overlay.click();
                        return 'clicked_overlay';
                    }
                }
                
                return 'no_close';
            })()
        """)
        
        return result in ['closed', 'clicked_overlay']
    
    def export_data_batched(
        self, 
        total_count: int, 
        batch_size: int = None,
        keyword: str = '',
        site_code: str = ''
    ) -> List[str]:
        """
        分批次导出数据
        
        Args:
            total_count: 总结果数
            batch_size: 每批次大小（默认100，知虾平台限制）
            keyword: 搜索关键词（用于文件命名）
            site_code: 站点代码（用于文件命名）
        
        Returns:
            导出的文件路径列表
        """
        if batch_size is None:
            batch_size = self.EXPORT_BATCH_SIZE
        
        # 计算批次数量
        batch_count = (total_count // batch_size) + (1 if total_count % batch_size else 0)
        logger.info(f"Total: {total_count}, Batches: {batch_count}, Batch size: {batch_size}")
        
        exported_files = []
        
        # 加载进度
        progress = self._load_progress()
        progress_key = f"{site_code}_{keyword}"
        completed_batches = progress.get(progress_key, {}).get('completed_batches', [])
        
        for batch_idx in range(batch_count):
            start = batch_idx * batch_size + 1
            end = min((batch_idx + 1) * batch_size, total_count)
            
            # 检查是否已完成
            if batch_idx in completed_batches:
                logger.info(f"Batch {batch_idx + 1} ({start}-{end}) already completed, skipping")
                continue
            
            logger.info(f"\n{'='*40}")
            logger.info(f"Batch {batch_idx + 1}/{batch_count}: {start} - {end}")
            logger.info(f"{'='*40}")
            
            # 点击导出按钮打开弹窗
            if not self._click_export_button():
                logger.warning("Export button not found, retrying...")
                time.sleep(2)
                self._click_export_button()
            
            time.sleep(2)
            
            # 设置导出范围
            if not self._set_export_range(start, end):
                logger.error(f"Failed to set range for batch {batch_idx + 1}")
                continue
            
            time.sleep(1)
            
            # 点击确认导出
            confirm_clicked = False
            for retry in range(3):
                if self._click_confirm_export():
                    confirm_clicked = True
                    break
                time.sleep(2)
            
            if not confirm_clicked:
                logger.error(f"Failed to confirm export for batch {batch_idx + 1}")
                self._close_export_modal()
                continue
            
            # 等待下载完成
            time.sleep(self.EXPORT_WAIT_TIME)
            filepath = self._wait_for_download(timeout=30)
            
            if filepath:
                exported_files.append(filepath)
                
                # 重命名文件（添加批次标识）
                if keyword and site_code:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    new_name = f"{site_code}_{keyword}_batch{batch_idx+1}_{timestamp}.xlsx"
                    new_path = os.path.join(self.download_dir, new_name)
                    try:
                        os.rename(filepath, new_path)
                        exported_files[-1] = new_path
                        logger.info(f"Renamed to: {new_name}")
                    except Exception as e:
                        logger.warning(f"Rename failed: {e}")
                
                # 更新进度
                completed_batches.append(batch_idx)
                progress[progress_key] = {
                    'total_count': total_count,
                    'batch_size': batch_size,
                    'completed_batches': completed_batches,
                    'last_update': datetime.now().isoformat()
                }
                self._save_progress(progress)
            else:
                logger.warning(f"No file downloaded for batch {batch_idx + 1}")
            
            # 关闭弹窗
            self._close_export_modal()
            time.sleep(2)
        
        # 清除进度（全部完成）
        if len(completed_batches) == batch_count:
            self._clear_progress()
        
        return exported_files
    
    def run_scrape(
        self,
        sites: List[str] = None,
        product_lines: List[str] = None,
        keyword_override: str = None,
    ) -> Dict:
        """
        执行采集任务
        
        Args:
            sites: 站点代码列表
            product_lines: 产品线代码列表
            keyword_override: 覆盖关键词（直接搜索指定关键词）
        
        Returns:
            采集结果字典
        """
        results = {
            'start_time': datetime.now().isoformat(),
            'tasks': [],
            'exports': [],
            'errors': []
        }
        
        if sites is None:
            sites = [s['code'] for s in self.config['sites']]
        
        if product_lines is None and not keyword_override:
            product_lines = list(self.config['product_lines'].keys())
        
        try:
            # 打开工作台
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
                
                # 如果有关键词覆盖，直接搜索该关键词
                if keyword_override:
                    keywords = [keyword_override]
                    pl_code = 'custom'
                else:
                    keywords = []
                    for pl_code in product_lines:
                        pl_info = self.config['product_lines'].get(pl_code)
                        if pl_info:
                            keywords.extend(pl_info['keywords'])
                
                for keyword in keywords:
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
                        
                        # 获取结果总数
                        total_count = self.get_result_count()
                        task['total_count'] = total_count
                        
                        if total_count == 0:
                            task['status'] = 'no_results'
                            results['errors'].append(task)
                            continue
                        
                        # 分批次导出
                        exported_files = self.export_data_batched(
                            total_count=total_count,
                            keyword=keyword.replace(' ', '_'),
                            site_code=site_code
                        )
                        
                        if exported_files:
                            task['status'] = 'success'
                            task['files'] = exported_files
                            task['file_count'] = len(exported_files)
                            results['exports'].extend(exported_files)
                            logger.info(f"Exported {len(exported_files)} files for {keyword}")
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
            self.cdp.close_tab()
        
        return results
    
    def save_results(self, results: Dict, output_path: str = None) -> None:
        """保存结果到 JSON 文件"""
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
    
    parser = argparse.ArgumentParser(description='知虾数据采集工具 (CDP版本 v2)')
    parser.add_argument('--config', '-c', default=None)
    parser.add_argument('--sites', '-s', nargs='+')
    parser.add_argument('--product-lines', '-p', nargs='+')
    parser.add_argument('--keyword', '-k', default=None, help='直接搜索指定关键词')
    
    args = parser.parse_args()
    
    scraper = ZhixiaCDPScraper(config_path=args.config)
    results = scraper.run_scrape(
        sites=args.sites,
        product_lines=args.product_lines,
        keyword_override=args.keyword
    )
    
    scraper.save_results(results)
    
    print(f"\n{'='*50}")
    print(f"Completed: {len(results['exports'])} files exported")
    print(f"Errors: {len(results['errors'])}")
    print(f"{'='*50}")
    
    if results.get('status') == 'login_failed':
        print(f"\n提示: {results.get('message')}")
    
    # 打印导出的文件列表
    if results['exports']:
        print("\n导出文件:")
        for f in results['exports']:
            print(f"  - {f}")


if __name__ == '__main__':
    main()