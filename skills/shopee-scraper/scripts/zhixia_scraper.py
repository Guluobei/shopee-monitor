#!/usr/bin/env python3
"""
知虾竞品数据采集脚本
使用Playwright自动化采集Shopee竞品数据
"""

import os
import sys
import json
import yaml
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
from playwright.sync_api import TimeoutError as PlaywrightTimeout

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ZhixiaScraper:
    """知虾竞品数据采集器"""

    def __init__(self, config_path: str = None):
        """初始化采集器"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__),
                '..', 'config', 'competitors.yaml'
            )

        self.config = self._load_config(config_path)
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Cookie保存路径
        self.cookie_file = os.path.join(
            os.path.dirname(__file__),
            '..', 'data', 'cookies.json'
        )
        os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)

        # 确保下载目录存在
        download_dir = os.path.abspath(self.config['browser']['download_dir'])
        os.makedirs(download_dir, exist_ok=True)

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def save_cookies(self) -> None:
        """保存cookies到文件"""
        try:
            cookies = self.context.cookies()
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            logger.info(f"Cookies已保存到: {self.cookie_file}")
        except Exception as e:
            logger.warning(f"保存Cookies失败: {e}")

    def load_cookies(self) -> bool:
        """从文件加载cookies"""
        if not os.path.exists(self.cookie_file):
            return False
        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            self.context.add_cookies(cookies)
            logger.info("Cookies已加载")
            return True
        except Exception as e:
            logger.warning(f"加载Cookies失败: {e}")
            return False

    def check_login_status(self) -> bool:
        """检查是否已登录"""
        try:
            # 访问知虾主页，检查是否跳转到了登录页
            self.page.goto(self.config['zhixia']['base_url'], wait_until='domcontentloaded', timeout=30000)
            time.sleep(3)

            # 等待页面稳定后再检查
            self.page.wait_for_load_state('networkidle', timeout=10000)

            # 检查最终URL
            current_url = self.page.url.lower()
            logger.info(f"检查登录状态，当前URL: {current_url}")

            # 检查URL是否包含登录相关字符
            login_indicators = ['login', 'signin', 'passport', 'auth', 'weixin', 'qrcode', 'base.monglar', '/workbench/login']

            for indicator in login_indicators:
                if indicator in current_url:
                    logger.warning(f"检测到未登录状态，URL包含: {indicator}")
                    return False

            # 额外检查：看看页面内容是否显示需要登录
            try:
                page_text = self.page.inner_text('body', timeout=3000)
                if '请登录' in page_text or '登录' in page_text[:500]:
                    logger.warning("页面内容显示需要登录")
                    return False
            except:
                pass

            logger.info("登录状态正常")
            return True
        except Exception as e:
            logger.warning(f"检查登录状态失败: {e}")
            return False

    def wait_for_manual_login(self, timeout: int = 120) -> bool:
        """等待用户手动登录"""
        logger.info("=" * 60)
        logger.info("请在打开的浏览器窗口中使用微信扫码登录知虾...")
        logger.info(f"请在 {timeout} 秒内完成登录")
        logger.info("=" * 60)

        # 打开可见的浏览器窗口
        try:
            self.browser.clear_cookies()
            self.page = self.context.new_page()
            self.page.goto(self.config['zhixia']['login_url'], wait_until='domcontentloaded')
        except:
            pass

        start_time = time.time()
        check_interval = 2  # 每2秒检查一次

        while time.time() - start_time < timeout:
            current_url = self.page.url.lower()

            # 检查是否已登录成功
            login_indicators = ['login', 'signin', 'passport', 'weixin', 'qrcode', 'base.monglar']
            is_logged_in = not any(ind in current_url for ind in login_indicators)

            if is_logged_in and (self.config['zhixia']['base_url'] in self.page.url or 'workbench' in self.page.url):
                logger.info("检测到登录成功!")
                self.save_cookies()
                return True

            time.sleep(check_interval)

        logger.warning("登录超时")
        return False

    def launch_browser(self, headless: bool = None) -> bool:
        """启动浏览器，返回是否成功登录"""
        logger.info("正在启动浏览器...")
        self.playwright = sync_playwright().start()

        if headless is None:
            headless = self.config['browser'].get('headless', False)

        self.browser = self.playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )

        # 创建带下载功能的上下文
        download_dir = os.path.abspath(self.config['browser']['download_dir'])
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            accept_downloads=True,
        )

        # 注入脚本隐藏自动化特征
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
        """)

        self.page = self.context.new_page()
        logger.info("浏览器启动成功")

        # 尝试加载cookies
        self.load_cookies()

        # 检查登录状态
        if not self.check_login_status():
            logger.warning("Cookies无效或未登录，需要重新登录")
            return False

        return True

    def close_browser(self) -> None:
        """关闭浏览器"""
        # 先保存cookies
        if self.context:
            self.save_cookies()

        try:
            if self.browser:
                self.browser.close()
                self.playwright.stop()
                logger.info("浏览器已关闭")
        except Exception as e:
            logger.warning(f"关闭浏览器时出错: {e}")
            try:
                self.playwright.stop()
            except:
                pass

    def navigate_to(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """导航到指定URL"""
        logger.info(f"正在访问: {url}")
        try:
            self.page.goto(url, wait_until=wait_until, timeout=60000)
            time.sleep(3)  # 等待页面稳定
        except PlaywrightTimeout:
            logger.warning("页面加载超时，尝试继续...")
            time.sleep(5)

    def select_site(self, site_code: str) -> None:
        """选择站点"""
        logger.info(f"正在切换站点: {site_code}")

        # 站点映射
        site_map = {
            'MY': '马来西亚',
            'ID': '印尼',
            'TH': '泰国',
            'PH': '菲律宾',
            'SG': '新加坡',
            'VN': '越南',
        }

        site_name = site_map.get(site_code, site_code)

        try:
            # 尝试直接点击站点链接（在页面底部的站点列表中）
            selectors = [
                f'a:has-text("{site_name}")',
                f'link:has-text("{site_name}")',
            ]

            for selector in selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element and element.is_visible():
                        element.click()
                        logger.info(f"站点切换成功: {site_code}")
                        time.sleep(3)
                        return
                except:
                    continue

            # 如果页面底部没有，尝试点击站点选择器按钮
            try:
                site_button = self.page.wait_for_selector(
                    'button:has-text("站点")',
                    timeout=3000
                )
                site_button.click()
                time.sleep(1)

                # 点击目标站点
                self.page.click(f'text={site_name}', timeout=5000)
                logger.info(f"站点切换成功: {site_code}")
                time.sleep(2)
            except Exception as e:
                logger.warning(f"站点切换失败: {e}")

        except Exception as e:
            logger.warning(f"选择站点时出错: {e}")

    def go_to_fuzzy_search(self) -> None:
        """进入产品模糊搜索页面"""
        logger.info("正在进入产品模糊搜索页面...")

        # 直接访问模糊搜索页面
        base_url = self.config['zhixia']['base_url']
        search_url = f"{base_url}/workbench/search/keyword-fuzzy-search?type=1&search=&searchType=2"

        try:
            self.navigate_to(search_url)
            # 等待页面完全加载
            time.sleep(5)
            self.page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(3)
            logger.info("已进入模糊搜索页面")
        except Exception as e:
            logger.error(f"直接访问失败: {e}")
            # 备选：通过首页导航
            self.navigate_to(self.config['zhixia']['base_url'])
            time.sleep(3)

            try:
                # 点击搜商品标签
                self.page.click('text=搜商品', timeout=5000)
                time.sleep(2)
            except Exception as e2:
                logger.warning(f"点击搜商品失败: {e2}")

    def search_keyword(self, keyword: str) -> None:
        """搜索关键词"""
        logger.info(f"正在搜索关键词: {keyword}")

        # URL编码关键词
        import urllib.parse
        encoded_keyword = urllib.parse.quote(keyword)

        try:
            # 直接通过URL访问搜索结果
            base_url = self.config['zhixia']['base_url']
            search_url = f"{base_url}/workbench/search/keyword-fuzzy-search?type=1&search={encoded_keyword}&searchType=2"

            self.navigate_to(search_url)

            # 等待页面完全加载
            time.sleep(5)
            self.page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(3)

            logger.info("搜索结果页面已加载")

        except Exception as e:
            logger.error(f"搜索失败: {e}")

            # 检查是否有搜索结果
            try:
                self.page.wait_for_selector(
                    'text=搜索结果数, text=个商品, [class*="table"]',
                    timeout=10000
                )
                logger.info("搜索结果已加载")
            except:
                logger.warning("未检测到明确的搜索结果")

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            raise

    def set_price_filter(self, min_price: float = None, max_price: float = None) -> None:
        """设置价格筛选"""
        if min_price is None and max_price is None:
            return

        logger.info(f"设置价格筛选: {min_price} - {max_price}")

        try:
            if min_price is not None:
                min_input = self.page.query_selector(
                    'input[placeholder*="最小价格"], input[placeholder*="min price"]'
                )
                if min_input:
                    min_input.fill(str(min_price))

            if max_price is not None:
                max_input = self.page.query_selector(
                    'input[placeholder*="最大价格"], input[placeholder*="max price"]'
                )
                if max_input:
                    max_input.fill(str(max_price))

            # 点击确定按钮
            self.page.click('button:has-text("确定")')
            time.sleep(2)

        except Exception as e:
            logger.warning(f"价格筛选设置失败: {e}")

    def get_search_results_count(self) -> int:
        """获取搜索结果数量"""
        try:
            # 从页面的分页信息中获取
            selectors = [
                'text=/\\d+个商品/',
                'text=/\\d+个结果/',
                '[class*="result"]',
                '[class*="count"]',
                # 知虾可能显示的格式
                'text=/\\d+条/',
                'text=/共\\d+/',
            ]

            for selector in selectors:
                try:
                    element = self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        text = element.inner_text()
                        # 提取数字
                        import re
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            return int(numbers[0])
                except:
                    continue

            # 如果页面有分页器，尝试从分页信息获取
            try:
                pagination = self.page.query_selector('[class*="pagination"], [class*="pager"]')
                if pagination:
                    text = pagination.inner_text()
                    import re
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        return int(numbers[-1])  # 通常最后一个数字是总页数或总数
            except:
                pass

            return 100  # 默认值
        except Exception as e:
            logger.warning(f"获取结果数量失败: {e}")
            return 100

    def export_data(self, output_filename: str = None, max_results: int = 500) -> Optional[str]:
        """
        导出数据

        Args:
            output_filename: 输出文件名
            max_results: 最大导出数量
        """
        logger.info("正在导出数据...")

        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"export_{timestamp}.xlsx"

        output_path = os.path.join(
            self.config['browser']['download_dir'],
            output_filename
        )

        try:
            # 确保页面加载完成
            time.sleep(3)
            self.page.wait_for_load_state("networkidle", timeout=10000)

            # 点击导出按钮 - 使用多种选择器
            export_selectors = [
                'button:has-text("导出")',
                'button:has-text("导 出")',
                '[class*="export"]',
                '[class*="导出"]',
            ]

            export_btn = None
            for selector in export_selectors:
                try:
                    export_btn = self.page.wait_for_selector(selector, timeout=3000)
                    if export_btn:
                        break
                except:
                    continue

            if export_btn:
                export_btn.click()
                logger.info("导出按钮已点击")
                time.sleep(2)
            else:
                logger.warning("未找到导出按钮，尝试截图分析...")
                self.page.screenshot(path="/tmp/export_debug.png")
                logger.info("截图已保存到 /tmp/export_debug.png")
                return None

            # 等待导出面板出现
            time.sleep(2)

            # 输入序号范围
            try:
                # 找到输入框
                inputs = self.page.query_selector_all('input')
                for inp in inputs:
                    try:
                        if inp.is_visible():
                            placeholder = inp.get_attribute('placeholder') or ''
                            if '请输入' in placeholder or 'min' in placeholder.lower():
                                inp.fill('1')
                                break
                    except:
                        continue

                time.sleep(0.5)

                # 找到最大序号输入框
                count = 0
                for inp in inputs:
                    try:
                        if inp.is_visible():
                            count += 1
                            if count == 2:
                                inp.fill(str(max_results))
                                break
                    except:
                        continue
            except Exception as e:
                logger.warning(f"输入序号失败: {e}")

            time.sleep(1)

            # 点击确认导出
            confirm_selectors = [
                'button:has-text("确认导出")',
                'button:has-text("确定")',
            ]

            for selector in confirm_selectors:
                try:
                    self.page.click(selector, timeout=3000)
                    logger.info("确认导出按钮已点击")
                    break
                except:
                    continue

            # 等待下载
            logger.info("等待下载完成...")
            time.sleep(10)

            return output_path

        except Exception as e:
            logger.error(f"导出失败: {e}")
            return None

            return 0

        except Exception as e:
            logger.warning(f"获取结果数量失败: {e}")
            return 0

    def wait_for_page_load(self, timeout: int = 30) -> bool:
        """等待页面加载完成"""
        try:
            self.page.wait_for_load_state("networkidle", timeout=timeout * 1000)
            time.sleep(2)
            return True
        except PlaywrightTimeout:
            logger.warning("页面加载超时")
            return False

    def close_popups(self) -> None:
        """关闭可能弹出的弹窗"""
        try:
            # 关闭验证码弹窗
            close_btns = [
                'button:has-text("Quit verification")',
                'button:has-text("关闭")',
                'button:has-text("×")',
                '[class*="close"]',
            ]

            for selector in close_btns:
                try:
                    self.page.click(selector, timeout=1000)
                    time.sleep(0.5)
                except:
                    pass

        except Exception as e:
            logger.debug(f"关闭弹窗时出错: {e}")

    def run_scrape(
        self,
        sites: List[str] = None,
        product_lines: List[str] = None,
        output_dir: str = None
    ) -> Dict:
        """
        执行采集任务

        Args:
            sites: 要采集的站点列表，如 ['MY', 'ID']
            product_lines: 要采集的产品线，如 ['OP', 'OM']
            output_dir: 输出目录

        Returns:
            采集结果统计
        """
        results = {
            'start_time': datetime.now().isoformat(),
            'tasks': [],
            'total_exports': 0,
            'errors': []
        }

        # 如果未指定站点，采集所有站点
        if sites is None:
            sites = [s['code'] for s in self.config['sites']]

        # 如果未指定产品线，采集所有产品线
        if product_lines is None:
            product_lines = list(self.config['product_lines'].keys())

        try:
            # 启动浏览器
            logged_in = self.launch_browser()

            if not logged_in:
                logger.info("尝试以可见模式启动浏览器以进行登录...")
                # 先关闭
                self.close_browser()
                time.sleep(2)

                # 以非headless模式重新启动
                self.launch_browser(headless=False)

                # 等待用户手动登录
                if not self.wait_for_manual_login(timeout=180):
                    logger.error("登录失败，无法继续采集")
                    results['status'] = 'login_failed'
                    return results

            # 访问知虾
            self.navigate_to(self.config['zhixia']['login_url'])
            time.sleep(3)

            # 关闭可能存在的弹窗
            self.close_popups()

            # 遍历站点
            for site_code in sites:
                site_info = next(
                    (s for s in self.config['sites'] if s['code'] == site_code),
                    None
                )
                if not site_info:
                    continue

                logger.info(f"\n{'='*50}")
                logger.info(f"开始采集站点: {site_info['name']} ({site_code})")
                logger.info(f"{'='*50}")

                # 切换站点
                self.select_site(site_code)
                time.sleep(2)

                # 遍历产品线
                for pl_code in product_lines:
                    pl_info = self.config['product_lines'].get(pl_code)
                    if not pl_info:
                        continue

                    logger.info(f"\n产品线: {pl_info['name']} ({pl_code})")

                    # 遍历关键词
                    for keyword in pl_info['keywords']:
                        task = {
                            'site': site_code,
                            'product_line': pl_code,
                            'keyword': keyword,
                            'timestamp': datetime.now().isoformat(),
                            'status': 'pending'
                        }

                        try:
                            # 进入模糊搜索
                            self.go_to_fuzzy_search()
                            time.sleep(2)

                            # 设置价格筛选（如果有）
                            if pl_info.get('min_price') or pl_info.get('max_price'):
                                self.set_price_filter(
                                    pl_info.get('min_price'),
                                    pl_info.get('max_price')
                                )

                            # 搜索关键词
                            self.search_keyword(keyword)
                            time.sleep(3)

                            # 关闭可能弹出的弹窗
                            self.close_popups()

                            # 生成输出文件名
                            filename = f"{site_code}_{pl_code}_{keyword.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"

                            # 导出数据
                            export_path = self.export_data(filename)

                            if export_path:
                                task['status'] = 'success'
                                task['output_file'] = export_path
                                results['total_exports'] += 1
                                logger.info(f"导出成功: {filename}")
                            else:
                                task['status'] = 'failed'
                                task['error'] = 'Export failed'

                        except Exception as e:
                            task['status'] = 'error'
                            task['error'] = str(e)
                            results['errors'].append(task)
                            logger.error(f"采集失败: {e}")

                        results['tasks'].append(task)

                        # 每个关键词之间休息一下
                        time.sleep(3)

            results['end_time'] = datetime.now().isoformat()
            results['status'] = 'completed'

        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            logger.error(f"采集过程出错: {e}")

        finally:
            self.close_browser()

        return results

    def save_results(self, results: Dict, output_path: str = None) -> None:
        """保存采集结果"""
        if output_path is None:
            output_dir = os.path.join(
                os.path.dirname(__file__),
                '..', 'output'
            )
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(
                output_dir,
                f"scrape_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"结果已保存: {output_path}")


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description='知虾竞品数据采集工具')
    parser.add_argument('--config', '-c', default=None, help='配置文件路径')
    parser.add_argument('--sites', '-s', nargs='+',
                        help='要采集的站点，如 MY ID TH')
    parser.add_argument('--product-lines', '-p', nargs='+',
                        help='要采集的产品线，如 OP OM MIC_400_1000')
    parser.add_argument('--output', '-o', default=None, help='输出目录')

    args = parser.parse_args()

    # 创建采集器
    scraper = ZhixiaScraper(config_path=args.config)

    # 执行采集
    results = scraper.run_scrape(
        sites=args.sites,
        product_lines=args.product_lines,
        output_dir=args.output
    )

    # 保存结果
    scraper.save_results(results)

    # 打印摘要
    print("\n" + "="*50)
    print("采集完成!")
    print(f"成功导出: {results['total_exports']} 个文件")
    print(f"错误数量: {len(results.get('errors', []))}")
    print("="*50)


if __name__ == '__main__':
    main()
