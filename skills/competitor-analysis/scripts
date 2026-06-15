#!/usr/bin/env python3
"""
知虾竞品数据处理器
解析下载的Excel文件，合并数据并生成标准化输出
"""

import os
import sys
import json
import yaml
import glob
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataProcessor:
    """竞品数据处理器"""

    # 知虾导出Excel的可能列名映射
    COLUMN_MAPPINGS = {
        # 商品信息
        '商品图片': ['商品图片', '图片', 'image', 'Image'],
        '商品ID': ['商品ID', 'item_id', 'ItemID', 'ProductID'],
        '商品名称': ['商品名称', '产品名称', '商品标题', '标题', 'name', 'Name', 'product_name', 'ProductName', 'title', 'Title'],
        '店铺名称': ['店铺名称', '店铺', 'shop', 'Shop', '店铺名', 'StoreName'],
        '店铺ID': ['店铺ID', 'shop_id', 'ShopID', 'StoreID'],
        '商品链接': ['商品链接', '链接', 'URL', 'url', 'Link', 'link'],

        # 价格信息
        '价格': ['价格', '商品价格', '售价', 'price', 'Price'],
        '原价': ['原价', '原价', 'original_price', 'OriginalPrice', 'market_price'],
        '折扣价': ['折扣价', 'discount_price', 'DiscountPrice'],

        # 销量信息
        '销量': ['销量', '销售量', '已售', 'sold', 'Sold', 'sales', 'Sales', 'sales_count'],
        '月销量': ['月销量', 'monthly_sales', 'MonthlySales'],
        '总销量': ['总销量', 'total_sales', 'TotalSales'],

        # 评分/评价
        '评分': ['评分', '店铺评分', 'rating', 'Rating'],
        '评价数': ['评价数', '评论数', 'reviews', 'Reviews', 'comment_count'],
        '店铺评价': ['店铺评价', 'shop_reviews'],

        # 商品数据
        '商品数量': ['商品数量', '商品数', 'item_count'],
        '关注人数': ['关注人数', '粉丝数', 'followers', 'Followers'],

        # 排名信息
        '排名': ['排名', 'rank', 'Rank'],
        '类目': ['类目', '类目名', 'category', 'Category'],
    }

    def __init__(self, config_path: str = None):
        """初始化处理器"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__),
                '..', 'config', 'competitors.yaml'
            )

        self.config = self._load_config(config_path)
        self.site_names = {s['code']: s['name'] for s in self.config['sites']}
        self.product_lines = self.config['product_lines']

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def find_downloaded_files(self, download_dir: str = None) -> List[str]:
        """查找已下载的Excel文件"""
        if download_dir is None:
            download_dir = os.path.abspath(self.config['browser']['download_dir'])

        patterns = [
            os.path.join(download_dir, '*.xlsx'),
            os.path.join(download_dir, '*.xls'),
        ]

        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern))

        # 过滤掉临时文件
        files = [f for f in files if not os.path.basename(f).startswith('~$')]

        logger.info(f"找到 {len(files)} 个Excel文件")
        return sorted(files, key=os.path.getmtime, reverse=True)

    def parse_filename(self, filepath: str) -> Dict[str, str]:
        """从文件名解析站点、产品线、关键词信息"""
        filename = os.path.basename(filepath)

        # 解析格式: {site}_{product_line}_{keyword}_{date}.xlsx
        parts = filename.replace('.xlsx', '').replace('.xls', '').split('_')

        result = {
            'site_code': parts[0] if len(parts) > 0 else 'UNKNOWN',
            'product_line': parts[1] if len(parts) > 1 else 'UNKNOWN',
            'keyword': '_'.join(parts[2:-1]) if len(parts) > 2 else 'UNKNOWN',
            'date': parts[-1] if len(parts) > 0 else datetime.now().strftime('%Y%m%d')
        }

        return result

    def standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        if df is None or df.empty:
            return df

        standardized = {}

        for standard_name, possible_names in self.COLUMN_MAPPINGS.items():
            for col in df.columns:
                col_lower = col.lower().strip()
                for possible_name in possible_names:
                    if col_lower == possible_name.lower() or col_lower in possible_name.lower():
                        standardized[standard_name] = col
                        break

        # 重命名列
        df_renamed = df.rename(columns=standardized)

        # 确保必要的列存在
        necessary_columns = ['商品名称', '价格', '销量']
        for col in necessary_columns:
            if col not in df_renamed.columns:
                logger.warning(f"缺少必要列: {col}")
                df_renamed[col] = None

        return df_renamed

    def read_excel_file(self, filepath: str) -> Optional[pd.DataFrame]:
        """读取Excel文件"""
        try:
            logger.info(f"正在读取: {filepath}")

            # 尝试不同的读取方式
            try:
                # 方式1: 正常读取
                df = pd.read_excel(filepath, engine='openpyxl')
            except Exception:
                try:
                    # 方式2: 使用xlrd引擎
                    df = pd.read_excel(filepath, engine='xlrd')
                except Exception:
                    # 方式3: 尝试所有sheet
                    all_sheets = pd.read_excel(filepath, sheet_name=None, engine='openpyxl')
                    if all_sheets:
                        df = list(all_sheets.values())[0]
                    else:
                        return None

            # 标准化列名
            df = self.standardize_columns(df)

            # 添加元数据
            metadata = self.parse_filename(filepath)
            df['采集站点'] = self.site_names.get(metadata['site_code'], metadata['site_code'])
            df['站点代码'] = metadata['site_code']
            df['产品线'] = self.product_lines.get(metadata['product_line'], {}).get('name', metadata['product_line'])
            df['产品线代码'] = metadata['product_line']
            df['搜索关键词'] = metadata['keyword']
            df['采集日期'] = metadata['date']
            df['原始文件名'] = os.path.basename(filepath)

            logger.info(f"成功读取 {len(df)} 行数据")
            return df

        except Exception as e:
            logger.error(f"读取文件失败 {filepath}: {e}")
            return None

    def clean_numeric(self, value: Any) -> Optional[float]:
        """清洗数值字段"""
        if pd.isna(value) or value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        # 转换为字符串处理
        str_value = str(value).strip()

        # 处理千分位逗号
        str_value = str_value.replace(',', '')

        # 处理货币符号
        for symbol in ['$', '¥', '€', '£', 'Rp', '฿', '₫', 'RM']:
            str_value = str_value.replace(symbol, '')

        # 处理"万"单位
        if '万' in str_value:
            try:
                return float(str_value.replace('万', '')) * 10000
            except:
                return None

        # 处理千单位
        if 'K' in str_value.upper():
            try:
                return float(str_value.upper().replace('K', '')) * 1000
            except:
                return None

        try:
            return float(str_value)
        except:
            return None

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清洗数据"""
        if df is None or df.empty:
            return df

        # 清洗数值字段
        numeric_columns = ['价格', '原价', '折扣价', '销量', '月销量', '总销量', '评价数', '评分', '排名']

        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].apply(self.clean_numeric)

        # 清洗商品名称 - 移除多余空白
        if '商品名称' in df.columns:
            df['商品名称'] = df['商品名称'].astype(str).str.strip()

        # 清洗店铺名称
        if '店铺名称' in df.columns:
            df['店铺名称'] = df['店铺名称'].astype(str).str.strip()

        # 移除空行
        if '商品名称' in df.columns:
            df = df.dropna(subset=['商品名称'])
            df = df[df['商品名称'] != 'nan']

        return df

    def deduplicate(self, df: pd.DataFrame, key_columns: List[str] = None) -> pd.DataFrame:
        """数据去重"""
        if df is None or df.empty:
            return df

        if key_columns is None:
            # 默认按商品名称+店铺去重
            key_columns = ['商品名称', '店铺名称']
            key_columns = [c for c in key_columns if c in df.columns]

        if key_columns:
            before_count = len(df)
            df = df.drop_duplicates(subset=key_columns, keep='last')
            removed = before_count - len(df)
            if removed > 0:
                logger.info(f"去重移除了 {removed} 条重复记录")

        return df

    def add_market_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加市场指标"""
        if df is None or df.empty:
            return df

        # 按站点和产品线计算市场份额
        if '销量' in df.columns and '站点代码' in df.columns:
            # 计算各站点总销量
            site_totals = df.groupby('站点代码')['销量'].sum().to_dict()

            # 计算各站点各产品线销量
            if '产品线代码' in df.columns:
                df['站点总销量'] = df['站点代码'].map(site_totals)
                df['站点产品线销量'] = df.groupby(['站点代码', '产品线代码'])['销量'].transform('sum')
                df['销量占比(%)'] = (df['销量'] / df['站点产品线销量'] * 100).round(2)

        # 计算价格竞争力（相对于同类产品）
        if '价格' in df.columns and '产品线代码' in df.columns:
            avg_prices = df.groupby('产品线代码')['价格'].mean().to_dict()
            df['产品线均价'] = df['产品线代码'].map(avg_prices)
            df['价格偏离度(%)'] = ((df['价格'] - df['产品线均价']) / df['产品线均价'] * 100).round(2)

        return df

    def merge_all_data(
        self,
        files: List[str] = None,
        download_dir: str = None
    ) -> pd.DataFrame:
        """
        合并所有数据文件

        Args:
            files: 指定文件列表，如果为None则自动查找下载目录
            download_dir: 下载目录路径

        Returns:
            合并后的DataFrame
        """
        if files is None:
            files = self.find_downloaded_files(download_dir)

        all_dataframes = []

        for filepath in files:
            df = self.read_excel_file(filepath)
            if df is not None and not df.empty:
                df = self.clean_data(df)
                all_dataframes.append(df)

        if not all_dataframes:
            logger.warning("没有找到有效数据")
            return pd.DataFrame()

        # 合并所有数据
        merged_df = pd.concat(all_dataframes, ignore_index=True)
        logger.info(f"合并后共 {len(merged_df)} 条记录")

        # 去重
        merged_df = self.deduplicate(merged_df)

        # 添加市场指标
        merged_df = self.add_market_indicators(merged_df)

        return merged_df

    def export_to_csv(
        self,
        df: pd.DataFrame,
        output_path: str = None,
        include_analysis: bool = True
    ) -> str:
        """
        导出为CSV文件

        Args:
            df: 要导出的数据
            output_path: 输出路径
            include_analysis: 是否包含分析列

        Returns:
            输出文件路径
        """
        if df is None or df.empty:
            logger.warning("没有数据可导出")
            return None

        if output_path is None:
            output_dir = os.path.abspath(
                self.config['output'].get('csv_dir', './output')
            )
            os.makedirs(output_dir, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            prefix = self.config['output'].get('file_prefix', 'shopee_competitor_data')
            output_path = os.path.join(output_dir, f'{prefix}_{timestamp}.csv')

        # 选择要导出的列
        export_columns = [
            '采集日期', '采集站点', '站点代码',
            '产品线', '产品线代码', '搜索关键词',
            '商品名称', '店铺名称',
            '价格', '原价',
            '销量', '月销量', '总销量',
            '评价数', '评分',
            '商品ID', '商品链接',
        ]

        # 如果包含分析指标
        if include_analysis:
            analysis_columns = [
                '站点总销量', '站点产品线销量', '销量占比(%)',
                '产品线均价', '价格偏离度(%)',
            ]
            export_columns.extend([c for c in analysis_columns if c in df.columns])

        # 只保留存在的列
        export_columns = [c for c in export_columns if c in df.columns]

        # 导出CSV
        df_export = df[export_columns].copy()

        # 排序
        df_export = df_export.sort_values(
            by=['采集日期', '站点代码', '产品线代码', '销量'],
            ascending=[False, True, True, False]
        )

        df_export.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"CSV已导出: {output_path}")

        return output_path

    def export_summary(
        self,
        df: pd.DataFrame,
        output_path: str = None
    ) -> str:
        """
        导出数据摘要

        Args:
            df: 数据
            output_path: 输出路径

        Returns:
            摘要文件路径
        """
        if df is None or df.empty:
            return None

        if output_path is None:
            output_dir = os.path.abspath(
                self.config['output'].get('consolidated_dir', './output/consolidated')
            )
            os.makedirs(output_dir, exist_ok=True)

            date_str = datetime.now().strftime('%Y%m%d')
            output_path = os.path.join(output_dir, f'summary_{date_str}.json')

        # 生成摘要
        summary = {
            '生成时间': datetime.now().isoformat(),
            '数据概况': {
                '总记录数': int(len(df)),
                '涉及站点': df['站点代码'].nunique() if '站点代码' in df.columns else 0,
                '涉及产品线': df['产品线代码'].nunique() if '产品线代码' in df.columns else 0,
                '涉及关键词': df['搜索关键词'].nunique() if '搜索关键词' in df.columns else 0,
                '涉及店铺': df['店铺名称'].nunique() if '店铺名称' in df.columns else 0,
            },
            '按站点统计': {},
            '按产品线统计': {},
            '热销商品Top10': [],
        }

        # 按站点统计
        if '站点代码' in df.columns:
            site_stats = df.groupby('站点代码').agg({
                '商品名称': 'count',
                '销量': 'sum' if '销量' in df.columns else 'count',
                '价格': ['mean', 'min', 'max'] if '价格' in df.columns else None,
            }).to_dict()

            for site in df['站点代码'].unique():
                site_data = df[df['站点代码'] == site]
                summary['按站点统计'][site] = {
                    '站点名称': self.site_names.get(site, site),
                    '商品数': int(len(site_data)),
                    '总销量': int(site_data['销量'].sum()) if '销量' in site_data.columns else 0,
                    '平均价格': round(site_data['价格'].mean(), 2) if '价格' in site_data.columns else 0,
                }

        # 按产品线统计
        if '产品线代码' in df.columns:
            for pl_code in df['产品线代码'].unique():
                pl_data = df[df['产品线代码'] == pl_code]
                pl_name = self.product_lines.get(pl_code, {}).get('name', pl_code)
                summary['按产品线统计'][pl_code] = {
                    '产品线名称': pl_name,
                    '商品数': int(len(pl_data)),
                    '总销量': int(pl_data['销量'].sum()) if '销量' in pl_data.columns else 0,
                    '平均价格': round(pl_data['价格'].mean(), 2) if '价格' in pl_data.columns else 0,
                    '涉及站点': list(pl_data['站点代码'].unique()),
                    '关键词': list(pl_data['搜索关键词'].unique()),
                }

        # 热销商品Top10
        if '销量' in df.columns and '商品名称' in df.columns:
            top_products = df.nlargest(10, '销量')[
                ['商品名称', '店铺名称', '销量', '价格', '站点代码', '产品线']
            ].to_dict('records')
            summary['热销商品Top10'] = top_products

        # 保存摘要
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        logger.info(f"摘要已导出: {output_path}")

        return output_path

    def run_process(
        self,
        download_dir: str = None,
        output_dir: str = None,
        export_all: bool = True
    ) -> Dict[str, str]:
        """
        运行完整的数据处理流程

        Args:
            download_dir: 下载目录
            output_dir: 输出目录
            export_all: 是否导出完整数据

        Returns:
            输出文件路径字典
        """
        results = {
            'processed_at': datetime.now().isoformat(),
            'files': {},
            'status': 'success'
        }

        try:
            # 查找下载的文件
            files = self.find_downloaded_files(download_dir)

            if not files:
                logger.warning("没有找到下载的文件")
                results['status'] = 'no_files'
                return results

            # 合并数据
            merged_df = self.merge_all_data(files)

            if merged_df.empty:
                results['status'] = 'empty_data'
                return results

            # 导出CSV
            if export_all:
                csv_path = self.export_to_csv(merged_df, output_dir)
                if csv_path:
                    results['files']['csv'] = csv_path

            # 导出摘要
            summary_path = self.export_summary(merged_df, output_dir)
            if summary_path:
                results['files']['summary'] = summary_path

            # 更新统计
            results['stats'] = {
                'total_records': len(merged_df),
                'sites': merged_df['站点代码'].nunique() if '站点代码' in merged_df.columns else 0,
                'product_lines': merged_df['产品线代码'].nunique() if '产品线代码' in merged_df.columns else 0,
            }

        except Exception as e:
            logger.error(f"处理失败: {e}")
            results['status'] = 'error'
            results['error'] = str(e)

        return results


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description='知虾竞品数据处理工具')
    parser.add_argument('--config', '-c', default=None, help='配置文件路径')
    parser.add_argument('--download-dir', '-d', default=None, help='下载目录')
    parser.add_argument('--output-dir', '-o', default=None, help='输出目录')
    parser.add_argument('--no-full-export', action='store_true', help='不导出完整数据')

    args = parser.parse_args()

    # 创建处理器
    processor = DataProcessor(config_path=args.config)

    # 执行处理
    results = processor.run_process(
        download_dir=args.download_dir,
        output_dir=args.output_dir,
        export_all=not args.no_full_export
    )

    # 打印结果
    print("\n" + "="*50)
    print("处理完成!")
    print(f"状态: {results['status']}")

    if results.get('stats'):
        print(f"处理记录数: {results['stats'].get('total_records', 0)}")
        print(f"涉及站点: {results['stats'].get('sites', 0)}")
        print(f"涉及产品线: {results['stats'].get('product_lines', 0)}")

    if results.get('files'):
        print("\n输出文件:")
        for key, path in results['files'].items():
            print(f"  {key}: {path}")

    print("="*50)


if __name__ == '__main__':
    main()
