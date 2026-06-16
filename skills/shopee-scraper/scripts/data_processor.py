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
        
        # 其他
        '商品数量': ['商品数量', '商品数', 'item_count'],
        '关注人数': ['关注人数', '粉丝数', 'followers', 'Followers'],
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
        self.site_names = {s['code']: s['name'] for s in self.config.get('sites', [])}
        self.product_lines = self.config.get('product_lines', {})
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def find_downloaded_files(self, download_dir: str = None) -> List[str]:
        """查找已下载的Excel文件"""
        if download_dir is None:
            download_dir = os.path.abspath(self.config.get('browser', {}).get('download_dir', './data/downloads'))
        
        patterns = [
            os.path.join(download_dir, '*.xlsx'),
            os.path.join(download_dir, '*.xls'),
        ]
        
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern))
        
        # 过滤临时文件
        files = [f for f in files if not os.path.basename(f).startswith('~$')]
        
        logger.info(f"找到 {len(files)} 个Excel文件")
        return sorted(files, key=os.path.getmtime, reverse=True)
    
    def parse_filename(self, filepath: str) -> Dict[str, str]:
        """从文件名解析站点、产品线、关键词信息"""
        filename = os.path.basename(filepath)
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
            
            # 尝试不同读取方式
            try:
                df = pd.read_excel(filepath, engine='openpyxl')
            except Exception:
                try:
                    df = pd.read_excel(filepath, engine='xlrd')
                except Exception:
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
        
        str_value = str(value).strip()
        str_value = str_value.replace(',', '')
        
        # 移除货币符号
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
        
        # 清洗商品名称
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
        
        # 按站点和产品线计算销量占比
        if '销量' in df.columns and '站点代码' in df.columns:
            site_totals = df.groupby('站点代码')['销量'].sum().to_dict()
            
            if '产品线代码' in df.columns:
                df['站点总销量'] = df['站点代码'].map(site_totals)
                df['站点产品线销量'] = df.groupby(['站点代码', '产品线代码'])['销量'].transform('sum')
                df['销量占比(%)'] = (df['销量'] / df['站点产品线销量'] * 100).round(2)
        
        # 计算价格竞争力
        if '价格' in df.columns and '产品线代码' in df.columns:
            avg_prices = df.groupby('产品线代码')['价格'].mean().to_dict()
            df['产品线均价'] = df['产品线代码'].map(avg_prices)
            df['价格偏离度(%)'] = ((df['价格'] - df['产品线均价']) / df['产品线均价'] * 100).round(2)
        
        return df
    
    def merge_all_data(self, files: List[str] = None, download_dir: str = None) -> pd.DataFrame:
        """合并所有数据文件"""
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
        
        # 合并
        merged_df = pd.concat(all_dataframes, ignore_index=True)
        logger.info(f"合并后共 {len(merged_df)} 条记录")
        
        # 去重
        merged_df = self.deduplicate(merged_df)
        
        # 添加市场指标
        merged_df = self.add_market_indicators(merged_df)
        
        return merged_df
    
    def export_to_csv(self, df: pd.DataFrame, output_path: str = None) -> str:
        """导出为CSV文件"""
        if df is None or df.empty:
            logger.warning("没有数据可导出")
            return None
        
        if output_path is None:
            output_dir = os.path.abspath(self.config.get('output', {}).get('csv_dir', './output'))
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            prefix = self.config.get('output', {}).get('file_prefix', 'shopee_competitor_data')
            output_path = os.path.join(output_dir, f'{prefix}_{timestamp}.csv')
        
        # 选择列
        export_columns = [
            '采集日期', '采集站点', '站点代码',
            '产品线', '产品线代码', '搜索关键词',
            '商品名称', '店铺名称',
            '价格', '原价',
            '销量', '月销量', '总销量',
            '评价数', '评分',
            '商品ID', '商品链接',
        ]
        
        # 分析列
        analysis_columns = [
            '站点总销量', '站点产品线销量', '销量占比(%)',
            '产品线均价', '价格偏离度(%)',
        ]
        export_columns.extend([c for c in analysis_columns if c in df.columns])
        
        # 只保留存在的列
        export_columns = [c for c in export_columns if c in df.columns]
        
        # 导出
        df_export = df[export_columns].copy()
        df_export = df_export.sort_values(
            by=['采集日期', '站点代码', '产品线代码', '销量'],
            ascending=[False, True, True, False]
        )
        df_export.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        logger.info(f"CSV已导出: {output_path}")
        return output_path
    
    def export_summary(self, df: pd.DataFrame, output_path: str = None) -> str:
        """导出数据摘要"""
        if df is None or df.empty:
            return None
        
        if output_path is None:
            output_dir = os.path.abspath(self.config.get('output', {}).get('consolidated_dir', './output/consolidated'))
            os.makedirs(output_dir, exist_ok=True)
            
            date_str = datetime.now().strftime('%Y%m%d')
            output_path = os.path.join(output_dir, f'summary_{date_str}.json')
        
        # 生成摘要
        summary = {
            '生成时间': datetime.now().isoformat(),
            '数据概况': {
                '总记录数': int(len(df)),
                '涉及站点': int(df['站点代码'].nunique()) if '站点代码' in df.columns else 0,
                '涉及产品线': int(df['产品线代码'].nunique()) if '产品线代码' in df.columns else 0,
                '涉及店铺': int(df['店铺名称'].nunique()) if '店铺名称' in df.columns else 0,
            },
            '按站点统计': {},
            '按产品线统计': {},
            '热销商品Top10': [],
        }
        
        # 按站点统计
        if '站点代码' in df.columns:
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
                }
        
        # 热销商品
        if '销量' in df.columns:
            top_products = df.nlargest(10, '销量')
            for _, row in top_products.iterrows():
                summary['热销商品Top10'].append({
                    '商品名称': row.get('商品名称', ''),
                    '店铺名称': row.get('店铺名称', ''),
                    '价格': float(row['价格']) if '价格' in row and pd.notna(row['价格']) else 0,
                    '销量': int(row['销量']) if '销量' in row and pd.notna(row['销量']) else 0,
                    '站点': row.get('采集站点', ''),
                })
        
        # 保存
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"摘要已导出: {output_path}")
        return output_path
    
    def run_process(self, download_dir: str = None, output_dir: str = None, export_all: bool = True) -> Dict:
        """运行完整处理流程"""
        logger.info("开始数据处理...")
        
        results = {
            'status': 'pending',
            'files': {},
        }
        
        try:
            # 合并数据
            df = self.merge_all_data(download_dir=download_dir)
            
            if df is None or df.empty:
                results['status'] = 'warning'
                results['message'] = '没有找到数据'
                return results
            
            results['stats'] = {
                'total_records': len(df),
                'unique_products': int(df['商品名称'].nunique()) if '商品名称' in df.columns else 0,
                'unique_shops': int(df['店铺名称'].nunique()) if '店铺名称' in df.columns else 0,
            }
            
            # 导出CSV
            if export_all:
                csv_file = self.export_to_csv(df)
                if csv_file:
                    results['files']['csv'] = csv_file
            
            # 导出摘要
            summary_file = self.export_summary(df)
            if summary_file:
                results['files']['summary'] = summary_file
            
            results['status'] = 'completed'
            
        except Exception as e:
            logger.error(f"处理异常: {e}")
            results['status'] = 'error'
            results['error'] = str(e)
        
        return results


if __name__ == '__main__':
    processor = DataProcessor()
    results = processor.run_process()
    print(json.dumps(results, ensure_ascii=False, indent=2))
