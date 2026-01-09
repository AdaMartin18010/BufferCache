#!/usr/bin/env python3
"""
BufferCache 项目代码示例测试框架

功能：
1. 扫描文档中的所有代码示例
2. 提取代码块
3. 测试代码可运行性
4. 生成测试报告

使用方法：
    python scripts/code_test_framework.py --scan-all
    python scripts/code_test_framework.py --test python
    python scripts/code_test_framework.py --report
"""

import re
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
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


@dataclass
class CodeBlock:
    """代码块信息"""
    file_path: Path
    language: str
    code: str
    line_start: int
    line_end: int
    context: str  # 代码块周围的上下文


class CodeExtractor:
    """代码提取器"""
    
    def __init__(self):
        self.code_block_pattern = re.compile(
            r'```(\w+)?\n(.*?)```',
            re.DOTALL
        )
    
    def extract_code_blocks(self, file_path: Path) -> List[CodeBlock]:
        """从Markdown文件中提取代码块"""
        code_blocks = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            matches = list(self.code_block_pattern.finditer(content))
            
            for match in matches:
                language = match.group(1) or 'text'
                code = match.group(2).strip()
                
                # 计算代码块在文件中的行号
                line_start = content[:match.start()].count('\n') + 1
                line_end = content[:match.end()].count('\n')
                
                # 提取上下文（代码块前后各3行）
                context_start = max(0, line_start - 4)
                context_end = min(len(lines), line_end + 4)
                context = '\n'.join(lines[context_start:context_end])
                
                code_block = CodeBlock(
                    file_path=file_path,
                    language=language,
                    code=code,
                    line_start=line_start,
                    line_end=line_end,
                    context=context
                )
                code_blocks.append(code_block)
        
        except Exception as e:
            logger.error(f"提取代码块失败 {file_path}: {e}")
        
        return code_blocks
    
    def scan_all_docs(self) -> Dict[str, List[CodeBlock]]:
        """扫描所有文档中的代码块"""
        all_blocks = {}
        
        logger.info("开始扫描所有文档...")
        
        for md_file in DOCS_DIR.rglob("*.md"):
            blocks = self.extract_code_blocks(md_file)
            if blocks:
                all_blocks[str(md_file.relative_to(PROJECT_ROOT))] = blocks
                logger.info(f"从 {md_file.name} 提取了 {len(blocks)} 个代码块")
        
        return all_blocks


class CodeTester:
    """代码测试器"""
    
    def __init__(self):
        self.test_results = []
    
    def test_python_code(self, code_block: CodeBlock) -> Tuple[bool, str]:
        """测试Python代码"""
        # 跳过一些明显不能独立运行的代码
        if any(skip in code_block.code for skip in ['...', '# TODO', '# FIXME']):
            return (True, "跳过：包含占位符或TODO")
        
        # 检查是否是完整可运行的代码
        if not self._is_runnable_python(code_block.code):
            return (True, "跳过：不是完整可运行代码（可能是代码片段）")
        
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code_block.code)
                temp_file = Path(f.name)
            
            # 执行代码
            result = subprocess.run(
                ['python', str(temp_file)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # 清理临时文件
            temp_file.unlink()
            
            if result.returncode == 0:
                return (True, "测试通过")
            else:
                return (False, f"执行失败: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            return (False, "执行超时")
        except Exception as e:
            return (False, f"测试出错: {str(e)}")
    
    def _is_runnable_python(self, code: str) -> bool:
        """判断Python代码是否可独立运行"""
        # 简单的启发式判断
        # 如果代码包含函数定义、类定义或顶层执行代码，可能是可运行的
        
        # 跳过明显的代码片段
        if code.count('\n') < 3:
            return False
        
        # 检查是否有import但没有使用
        if 'import' in code and not any(keyword in code for keyword in ['def ', 'class ', 'if __name__', 'print(', '=']):
            return False
        
        # 如果有函数或类定义，认为是可运行的
        if re.search(r'^(def |class |if __name__)', code, re.MULTILINE):
            return True
        
        # 如果有顶层执行代码（不是注释），认为是可运行的
        lines = [line.strip() for line in code.split('\n') if line.strip() and not line.strip().startswith('#')]
        if len(lines) >= 3:
            return True
        
        return False
    
    def test_all_code(self, all_blocks: Dict[str, List[CodeBlock]], language: str = None) -> List[Dict]:
        """测试所有代码"""
        results = []
        
        logger.info(f"开始测试代码（语言: {language or 'all'}）...")
        
        for file_path, blocks in all_blocks.items():
            for block in blocks:
                if language and block.language != language:
                    continue
                
                if block.language == 'python':
                    success, message = self.test_python_code(block)
                    results.append({
                        'file': file_path,
                        'language': block.language,
                        'line_start': block.line_start,
                        'line_end': block.line_end,
                        'success': success,
                        'message': message
                    })
                else:
                    # 其他语言的测试待实现
                    results.append({
                        'file': file_path,
                        'language': block.language,
                        'line_start': block.line_start,
                        'line_end': block.line_end,
                        'success': None,
                        'message': f"语言 {block.language} 的测试待实现"
                    })
        
        return results
    
    def generate_test_report(self, results: List[Dict]) -> str:
        """生成测试报告"""
        total = len(results)
        passed = sum(1 for r in results if r['success'] is True)
        failed = sum(1 for r in results if r['success'] is False)
        skipped = sum(1 for r in results if r['success'] is None)
        
        report_lines = [
            "# BufferCache 项目代码测试报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 测试统计",
            "",
            f"- **总代码块数**: {total}",
            f"- **测试通过**: {passed}",
            f"- **测试失败**: {failed}",
            f"- **跳过/待实现**: {skipped}",
            f"- **通过率**: {passed/total*100:.1f}%" if total > 0 else "- **通过率**: 0%",
            "",
            "## 详细结果",
            ""
        ]
        
        # 按文件分组
        by_file = {}
        for result in results:
            file = result['file']
            if file not in by_file:
                by_file[file] = []
            by_file[file].append(result)
        
        for file, file_results in sorted(by_file.items()):
            report_lines.append(f"### {file}")
            report_lines.append("")
            
            for result in file_results:
                status = "✅" if result['success'] is True else "❌" if result['success'] is False else "⏭️"
                report_lines.append(
                    f"- {status} 行 {result['line_start']}-{result['line_end']} "
                    f"({result['language']}): {result['message']}"
                )
            
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def save_report(self, report: str, filename: str = "code_test_report.md"):
        """保存报告到文件"""
        report_path = PROJECT_ROOT / "reports" / filename
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(report, encoding='utf-8')
        logger.info(f"测试报告已保存到: {report_path}")


def main():
    parser = argparse.ArgumentParser(description='BufferCache项目代码测试框架')
    parser.add_argument('--scan-all', action='store_true',
                       help='扫描所有文档中的代码块')
    parser.add_argument('--test', choices=['python', 'all'],
                       help='测试指定语言的代码')
    parser.add_argument('--report', action='store_true',
                       help='生成测试报告')
    
    args = parser.parse_args()
    
    extractor = CodeExtractor()
    tester = CodeTester()
    
    if args.scan_all:
        all_blocks = extractor.scan_all_docs()
        print(f"\n扫描完成，共找到 {sum(len(blocks) for blocks in all_blocks.values())} 个代码块")
        
        # 统计各语言的代码块数量
        lang_count = {}
        for blocks in all_blocks.values():
            for block in blocks:
                lang_count[block.language] = lang_count.get(block.language, 0) + 1
        
        print("\n代码块语言分布:")
        for lang, count in sorted(lang_count.items(), key=lambda x: -x[1]):
            print(f"  {lang}: {count}")
    
    if args.test:
        all_blocks = extractor.scan_all_docs()
        results = tester.test_all_code(all_blocks, args.test)
        report = tester.generate_test_report(results)
        tester.save_report(report)
        print("\n" + "="*60)
        print(report)
        print("="*60)


if __name__ == "__main__":
    main()
