#!/usr/bin/env python3
"""
Marvis 环境适配器 - Shopee 竞品监控套件
将 TRAE Skill 格式适配到 Marvis Agent 环境

改动：
1. 使用系统 Chrome (channel="chrome") 替代 Playwright Chromium
2. 路径动态化，不再硬编码
3. 提供统一入口函数
4. 支持无头模式默认运行
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Optional

# 固定仓库根目录
REPO_ROOT = Path(__file__).parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "shopee-scraper" / "scripts"
CONFIG_PATH = REPO_ROOT / "config" / "competitors.yaml"
DATA_DIR = REPO_ROOT / "data"
OUTPUT_DIR = REPO_ROOT / "output"

# 确保目录存在
for d in [DATA_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 添加脚本目录到 sys.path
sys.path.insert(0, str(SCRIPTS_DIR))


class MarvisShopeeMonitor:
    """Marvis 环境下的 Shopee 竞品监控入口"""

    def __init__(self, headless: bool = True, username: str = None, password: str = None):
        """
        Args:
            headless: 是否无头模式
            username: 知虾账号（可选，用于账号密码登录）
            password: 知虾密码（可选，仅内存中使用，不持久化）
        """
        self.headless = headless
        self.username = username
        self.password = password
        self.results = {}

    def check_environment(self) -> Dict:
        """检查运行环境"""
        issues = []
        warnings = []

        # 1. 检查 Python 依赖 (注意 pyyaml 的 import 名是 yaml)
        import_map = {"playwright": "playwright", "pandas": "pandas", "pyyaml": "yaml", "openpyxl": "openpyxl"}
        for pkg, imp_name in import_map.items():
            try:
                __import__(imp_name)
            except ImportError:
                issues.append(f"缺少依赖: {pkg}")

        # 2. 检查 Chrome
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        chrome_found = any(Path(p).exists() for p in chrome_paths)
        if not chrome_found:
            warnings.append("未找到系统 Chrome，将尝试使用 Playwright Chromium")

        # 3. 检查配置文件
        if not CONFIG_PATH.exists():
            issues.append(f"配置文件缺失: {CONFIG_PATH}")

        # 4. 检查知虾平台可达性
        from urllib.request import urlopen, Request
        try:
            req = Request("https://shopee.menglar.com", headers={"User-Agent": "Mozilla/5.0"})
            urlopen(req, timeout=10)
            warnings.append("知虾平台可达（如首次使用需扫码登录）")
        except Exception:
            warnings.append("知虾平台不可达，请检查网络")

        return {
            "status": "ok" if not issues else "blocked",
            "issues": issues,
            "warnings": warnings,
            "chrome_found": chrome_found,
            "python_version": sys.version.split()[0],
        }

    def scrape(self, sites: list = None, product_lines: list = None,
               keywords: list = None, max_count: int = 500) -> Dict:
        """执行数据采集"""
        from zhixia_scraper import ZhixiaScraper

        scraper = ZhixiaScraper(config_path=str(CONFIG_PATH))

        # 使用系统 Chrome 替代 Playwright Chromium
        # 重写 launch_browser 使用 channel="chrome"
        original_launch = scraper.launch_browser

        def patched_launch(headless=None):
            if headless is None:
                headless = self.headless

            scraper.playwright = __import__('playwright.sync_api',
                                           fromlist=['sync_playwright']).sync_playwright().start()

            launch_args = {
                'headless': headless,
                'channel': 'chrome',  # 使用系统 Chrome
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                ]
            }
            scraper.browser = scraper.playwright.chromium.launch(**launch_args)

            scraper.context = scraper.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                accept_downloads=True,
            )
            scraper.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
            """)
            scraper.page = scraper.context.new_page()
            scraper.load_cookies()

            # 检查登录状态
            try:
                scraper.page.goto(scraper.config['zhixia']['base_url'],
                                 wait_until='domcontentloaded', timeout=30000)
                time.sleep(3)
                current_url = scraper.page.url.lower()
                if any(p in current_url for p in ['login', 'signin', 'passport', 'auth']):
                    # 优先尝试账号密码登录
                    if self.username and self.password:
                        print("检测到登录页面，使用账号密码自动登录...")
                        try:
                            from zhixia_login import ZhixiaLoginManager
                            login_mgr = ZhixiaLoginManager(
                                config=None,
                                cookie_file=str(DATA_DIR / "cookies.json"),
                                screenshot_dir=str(DATA_DIR / "screenshots"),
                            )
                            login_mgr.browser = scraper.browser
                            login_mgr.context = scraper.context
                            login_mgr.page = scraper.page
                            login_mgr.playwright = scraper.playwright

                            success, status = login_mgr.ensure_login_with_credentials(
                                username=self.username,
                                password=self.password,
                                force_visible=True,
                                auto_login_timeout=120,
                            )
                            if success:
                                print(f"账号密码登录成功: {status}")
                                scraper.save_cookies()
                                return True
                            else:
                                print(f"账号密码登录失败: {status}，降级为手动扫码...")
                        except Exception as e:
                            print(f"凭据登录异常: {e}，降级为手动扫码...")

                    # 降级：手动扫码登录
                    print("请手动扫码登录...")
                    print("等待登录完成（最多3分钟）...")
                    time.sleep(180)
                    current_url = scraper.page.url.lower()
                    if any(p in current_url for p in ['login', 'signin', 'passport', 'auth']):
                        return False
                scraper.save_cookies()
                return True
            except Exception as e:
                print(f"登录检查失败: {e}")
                return False

        scraper.launch_browser = patched_launch

        results = scraper.run_scrape(sites=sites, product_lines=product_lines)
        return results

    def process(self, download_dir: str = None) -> Dict:
        """处理已下载的数据"""
        from data_processor import DataProcessor

        processor = DataProcessor(config_path=str(CONFIG_PATH))
        return processor.run_process(download_dir=download_dir)

    def run_full_pipeline(self, sites: list = None, product_lines: list = None,
                          download_dir: str = None) -> Dict:
        """运行完整流水线：采集 → 处理 → 导出"""
        pipeline_result = {
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "environment": self.check_environment(),
        }

        if pipeline_result["environment"]["status"] == "blocked":
            pipeline_result["status"] = "environment_blocked"
            return pipeline_result

        # 阶段1：采集
        print("=" * 50)
        print("阶段1: 数据采集")
        print("=" * 50)
        try:
            scrape_result = self.scrape(sites=sites, product_lines=product_lines)
            pipeline_result["scrape"] = scrape_result
            if scrape_result.get("status") != "completed":
                pipeline_result["status"] = "scrape_failed"
                return pipeline_result
        except Exception as e:
            pipeline_result["scrape"] = {"status": "error", "error": str(e)}
            pipeline_result["status"] = "scrape_error"
            return pipeline_result

        # 阶段2：处理
        print("=" * 50)
        print("阶段2: 数据处理")
        print("=" * 50)
        try:
            process_result = self.process(download_dir=download_dir)
            pipeline_result["process"] = process_result
        except Exception as e:
            pipeline_result["process"] = {"status": "error", "error": str(e)}
            pipeline_result["status"] = "partial"

        pipeline_result["status"] = "completed"
        pipeline_result["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        return pipeline_result


def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description="Shopee 竞品监控 - Marvis 适配版")
    parser.add_argument("--check", action="store_true", help="仅检查环境")
    parser.add_argument("--sites", nargs="+", default=["MY"], help="目标站点代码")
    parser.add_argument("--product-lines", nargs="+", default=["OP"], help="产品线代码")
    parser.add_argument("--headless", type=bool, default=True, help="是否无头模式")
    parser.add_argument("--process-only", action="store_true", help="仅处理已有数据")
    parser.add_argument("--download-dir", default=None, help="已下载数据的目录")
    parser.add_argument("--username", default=None, help="知虾账号（手机号/邮箱）")
    parser.add_argument("--password", default=None, help="知虾密码（不持久化）")

    args = parser.parse_args()
    monitor = MarvisShopeeMonitor(
        headless=args.headless,
        username=args.username,
        password=args.password,
    )

    if args.check:
        env = monitor.check_environment()
        print(json.dumps(env, ensure_ascii=False, indent=2))
        return

    if args.process_only:
        result = monitor.process(download_dir=args.download_dir)
    else:
        result = monitor.run_full_pipeline(
            sites=args.sites,
            product_lines=args.product_lines,
            download_dir=args.download_dir,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
