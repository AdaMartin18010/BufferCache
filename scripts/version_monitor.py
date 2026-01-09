#!/usr/bin/env python3
"""
BufferCache 项目版本监控脚本

功能：
1. 监控Redis、操作系统、数据库等关键技术的版本更新
2. 检测新版本发布
3. 生成版本更新报告
4. 自动更新文档中的版本信息

使用方法：
    python scripts/version_monitor.py --check-all
    python scripts/version_monitor.py --check redis
    python scripts/version_monitor.py --update-docs
"""

import requests
import json
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"


class VersionMonitor:
    """版本监控器"""
    
    def __init__(self):
        self.redis_github_api = "https://api.github.com/repos/redis/redis/releases/latest"
        self.redis_downloads = "https://download.redis.io/releases/"
        self.current_versions = self._load_current_versions()
        
    def _load_current_versions(self) -> Dict[str, str]:
        """加载当前文档中的版本信息"""
        versions = {}
        
        # 从文档中提取Redis版本信息
        redis_version_pattern = r'Redis\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)'
        
        for md_file in DOCS_DIR.rglob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                matches = re.findall(redis_version_pattern, content, re.IGNORECASE)
                if matches:
                    # 取最高版本
                    versions['redis'] = max(matches, key=lambda v: tuple(map(int, v.split('.'))))
            except Exception as e:
                logger.warning(f"读取文件失败 {md_file}: {e}")
        
        return versions
    
    def check_redis_version(self) -> Optional[Tuple[str, str]]:
        """检查Redis最新版本"""
        try:
            response = requests.get(self.redis_github_api, timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_version = data['tag_name'].lstrip('v')  # 移除'v'前缀
                published_at = data['published_at']
                
                current_version = self.current_versions.get('redis', '7.0')
                
                logger.info(f"Redis当前文档版本: {current_version}")
                logger.info(f"Redis最新发布版本: {latest_version}")
                
                if self._compare_versions(latest_version, current_version) > 0:
                    return (latest_version, current_version)
                else:
                    logger.info("Redis版本已是最新")
                    return None
            else:
                logger.error(f"获取Redis版本失败: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"检查Redis版本时出错: {e}")
            return None
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """比较两个版本号
        返回: 1 if v1 > v2, -1 if v1 < v2, 0 if v1 == v2
        """
        def version_tuple(v: str):
            parts = v.split('.')
            return tuple(int(part) for part in parts)
        
        t1 = version_tuple(v1)
        t2 = version_tuple(v2)
        
        if t1 > t2:
            return 1
        elif t1 < t2:
            return -1
        else:
            return 0
    
    def check_all_versions(self) -> Dict[str, Optional[Tuple[str, str]]]:
        """检查所有技术的版本"""
        results = {}
        
        logger.info("开始检查所有技术版本...")
        
        # 检查Redis
        redis_result = self.check_redis_version()
        results['redis'] = redis_result
        
        # 可以添加其他技术的检查
        # results['mysql'] = self.check_mysql_version()
        # results['postgresql'] = self.check_postgresql_version()
        
        return results
    
    def generate_version_report(self, results: Dict[str, Optional[Tuple[str, str]]]) -> str:
        """生成版本更新报告"""
        report_lines = [
            "# BufferCache 项目版本更新报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 版本检查结果",
            ""
        ]
        
        for tech, result in results.items():
            if result:
                latest, current = result
                report_lines.extend([
                    f"### {tech.upper()}",
                    f"- **当前文档版本**: {current}",
                    f"- **最新发布版本**: {latest}",
                    f"- **状态**: ⚠️ **需要更新**",
                    f"- **建议**: 更新所有相关文档中的版本信息",
                    ""
                ])
            else:
                report_lines.extend([
                    f"### {tech.upper()}",
                    f"- **状态**: ✅ **已是最新版本**",
                    ""
                ])
        
        report_lines.extend([
            "## 更新建议",
            "",
            "1. 对于需要更新的技术版本：",
            "   - 更新文档中的版本号",
            "   - 检查新版本的新特性",
            "   - 更新相关代码示例",
            "   - 更新配置示例",
            "",
            "2. 创建版本更新任务：",
            "   - 在GitHub Issues中创建版本更新任务",
            "   - 分配负责人",
            "   - 设置截止日期",
            ""
        ])
        
        return "\n".join(report_lines)
    
    def save_report(self, report: str, filename: str = "version_report.md"):
        """保存报告到文件"""
        report_path = PROJECT_ROOT / "reports" / filename
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(report, encoding='utf-8')
        logger.info(f"版本报告已保存到: {report_path}")


def main():
    parser = argparse.ArgumentParser(description='BufferCache项目版本监控工具')
    parser.add_argument('--check', choices=['redis', 'all'], default='all',
                       help='检查指定技术或所有技术')
    parser.add_argument('--check-all', action='store_true',
                       help='检查所有技术版本')
    parser.add_argument('--update-docs', action='store_true',
                       help='自动更新文档中的版本信息（待实现）')
    parser.add_argument('--output', default='version_report.md',
                       help='报告输出文件名')
    
    args = parser.parse_args()
    
    monitor = VersionMonitor()
    
    if args.check_all or args.check == 'all':
        results = monitor.check_all_versions()
        report = monitor.generate_version_report(results)
        monitor.save_report(report, args.output)
        print("\n" + "="*60)
        print(report)
        print("="*60)
    elif args.check == 'redis':
        result = monitor.check_redis_version()
        if result:
            latest, current = result
            print(f"\nRedis版本更新检测:")
            print(f"  当前文档版本: {current}")
            print(f"  最新发布版本: {latest}")
            print(f"  状态: ⚠️ 需要更新")
        else:
            print("\nRedis版本已是最新")
    
    if args.update_docs:
        logger.info("文档自动更新功能待实现")
        # TODO: 实现文档自动更新功能


if __name__ == "__main__":
    main()
