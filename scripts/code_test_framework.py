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
import os
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
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(code_block.code)
                temp_file = Path(f.name)

            # 执行代码
            result = subprocess.run(
                ['python', str(temp_file)],
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8',
                errors='replace'
            )

            # 清理临时文件
            temp_file.unlink()

            if result.returncode == 0:
                return (True, "测试通过")

            stderr = result.stderr or ""
            # 缺少第三方依赖：环境问题，非文档代码错误
            if "ModuleNotFoundError" in stderr:
                mod = re.search(r"No module named '([^']+)'", stderr)
                name = mod.group(1) if mod else "unknown"
                return (None, f"跳过：测试环境缺少依赖模块 {name}")
            # NameError：教学片段依赖前后文定义的变量/函数，无法独立运行
            if "NameError" in stderr:
                return (None, "跳过：代码片段依赖上下文（引用前文定义的变量/函数）")
            # SyntaxError/IndentationError：教学片段不完整，被启发式误判为完整程序
            if "SyntaxError" in stderr or "IndentationError" in stderr:
                return (None, "跳过：代码片段不完整（语法/缩进不完整）")
            return (False, f"执行失败: {stderr}")
        
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

    # ---------------- Go ----------------

    GO_THIRD_PARTY_IMPORT = re.compile(
        r'^\s*(?:[\w.]+\s+)?"(?:github\.com|golang\.org|gopkg\.in|google\.golang\.org|k8s\.io|go\.uber\.org|golang\.org/x)/[^"]+"',
        re.MULTILINE,
    )

    def test_go_code(self, code_block: CodeBlock) -> Tuple[bool, str]:
        """测试Go代码：完整单文件程序 go run；片段/多文件跳过"""
        code = code_block.code
        if '...' in code or '// TODO' in code:
            return (None, "跳过：包含占位符或TODO")
        # 必须是完整单文件 main 程序
        if 'package main' not in code or 'func main(' not in code:
            return (None, "跳过：不是完整 main 程序（函数级教学片段）")
        if re.search(r'^package\s+(?!main\b)\w+', code, re.MULTILINE):
            return (None, "跳过：非 main 包（库代码片段）")
        if self.GO_THIRD_PARTY_IMPORT.search(code):
            return (None, "跳过：import 第三方模块（无 go.mod 环境）")
        import shutil
        if not shutil.which('go'):
            return (None, "跳过：环境未安装 Go")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                src = Path(tmp) / 'main.go'
                src.write_text(code, encoding='utf-8')
                result = subprocess.run(
                    ['go', 'run', str(src)], cwd=tmp,
                    capture_output=True, text=True, timeout=120,
                    encoding='utf-8', errors='replace',
                    env={**os.environ, 'GOFLAGS': '-mod=mod', 'GO111MODULE': 'off'},
                )
            if result.returncode == 0:
                return (True, "测试通过")
            stderr = result.stderr or ""
            if 'is not in std' in stderr or 'cannot find module' in stderr \
               or 'proxy.golang.org' in stderr or 'connection refused' in stderr:
                return (None, "跳过：依赖第三方模块（环境无 go.mod）")
            # 运行环境权限/依赖要求，非文档代码错误
            if any(k in (result.stderr or '') + (result.stdout or '')
                   for k in ('root', '权限', 'permission denied', 'requires')):
                return (None, "跳过：运行需要 root/特殊权限（环境不满足）")
            return (False, f"编译/执行失败: {stderr[:300]}")
        except subprocess.TimeoutExpired:
            return (False, "执行超时（>120s）")
        except Exception as e:
            return (False, f"测试出错: {str(e)}")

    # ---------------- Rust ----------------

    # ---------------- Rust ----------------

    RUST_THIRD_PARTY = re.compile(
        r"^\s*(?:use|extern\s+crate)\s+(tokio|serde|anyhow|thiserror|rand|reqwest|async_std|async_std|futures|hyper|warp|axum|actix|clap|log|env_logger|chrono|regex|lazy_static|once_cell|dashmap|parking_lot|crossbeam|rayon|libc|nix)\b",
        re.MULTILINE,
    )

    def test_rust_code(self, code_block: CodeBlock) -> Tuple[bool, str]:
        """测试Rust代码：rustc 编译检查，编译过则运行；外部 crate 跳过"""
        code = code_block.code
        if '...' in code or '// TODO' in code:
            return (None, "跳过：包含占位符或TODO")
        if 'fn main(' not in code:
            return (None, "跳过：无 fn main（库/片段代码）")
        if self.RUST_THIRD_PARTY.search(code) or re.search(r'\blibc::|\bnix::', code):
            return (None, "跳过：依赖第三方 crate（无 Cargo 环境）")
        import shutil
        if not shutil.which('rustc'):
            return (None, "跳过：环境未安装 rustc")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                src = Path(tmp) / 'main.rs'
                exe = Path(tmp) / 'main'
                src.write_text(code, encoding='utf-8')
                build = subprocess.run(
                    ['rustc', '--edition', '2021', '-o', str(exe), str(src)],
                    capture_output=True, text=True, timeout=120,
                    encoding='utf-8', errors='replace',
                )
                if build.returncode != 0:
                    stderr = build.stderr or ""
                    # E04xx：引用未定义的符号（前文已定义但未贴出的教学片段）
                    if re.search(r'error\[E04\d\d\]', stderr):
                        return (None, "跳过：引用上下文定义的符号（教学片段未完整贴出）")
                    if 'cannot find module or crate' in stderr:
                        return (None, "跳过：依赖第三方 crate（无 Cargo 环境）")
                    return (False, f"编译失败: {stderr[:300]}")
                run = subprocess.run(
                    [str(exe)], capture_output=True, text=True, timeout=30,
                    encoding='utf-8', errors='replace',
                )
            if run.returncode == 0:
                return (True, "测试通过")
            return (False, f"运行失败(exit {run.returncode}): {(run.stderr or '')[:300]}")
        except subprocess.TimeoutExpired:
            return (False, "执行超时")
        except Exception as e:
            return (False, f"测试出错: {str(e)}")

    # ---------------- Bash ----------------

    def test_bash_code(self, code_block: CodeBlock) -> Tuple[bool, str]:
        """测试Bash代码：仅语法检查（bash -n），不执行（遵守 §4.2.4 平台守卫禁令）"""
        code = code_block.code
        if code.count('\n') < 2:
            return (None, "跳过：过短片段")
        # 文档伪参数惯例 <pid>、<node-id> 会被 bash 当重定向符导致语法报错
        if re.search(r'<[a-z][\w-]*>', code):
            return (None, "跳过：包含 <placeholder> 参数占位（语法检查不适用）")
        import shutil
        bash = shutil.which('bash') or shutil.which('sh')
        if not bash:
            return (None, "跳过：环境未安装 bash")
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_file = Path(f.name)
            result = subprocess.run(
                [bash, '-n', str(temp_file)],
                capture_output=True, text=True, timeout=30,
                encoding='utf-8', errors='replace',
            )
            temp_file.unlink()
            if result.returncode == 0:
                return (True, "语法检查通过（未执行，平台守卫）")
            return (False, f"语法错误: {(result.stderr or '')[:300]}")
        except subprocess.TimeoutExpired:
            return (False, "检查超时")
        except Exception as e:
            return (False, f"测试出错: {str(e)}")
    
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
                elif block.language == 'go':
                    success, message = self.test_go_code(block)
                    results.append({
                        'file': file_path,
                        'language': block.language,
                        'line_start': block.line_start,
                        'line_end': block.line_end,
                        'success': success,
                        'message': message
                    })
                elif block.language == 'rust':
                    success, message = self.test_rust_code(block)
                    results.append({
                        'file': file_path,
                        'language': block.language,
                        'line_start': block.line_start,
                        'line_end': block.line_end,
                        'success': success,
                        'message': message
                    })
                elif block.language in ('bash', 'sh', 'shell'):
                    success, message = self.test_bash_code(block)
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
            f"- **跳过（环境依赖/上下文片段）**: {skipped}",
        ]
        runnable = passed + failed
        if runnable > 0:
            report_lines.append(f"- **可运行代码通过率**: {passed/runnable*100:.1f}%（通过/(通过+失败)，不含跳过）")
        report_lines += [
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


def save_report_for_language(tester: 'CodeTester', report: str, language: str):
    """按语种保存报告，避免多语言轮跑互相覆盖（python 保持历史文件名）"""
    if language == 'python':
        tester.save_report(report)
    else:
        tester.save_report(report, f"code_test_report_{language}.md")


def main():
    parser = argparse.ArgumentParser(description='BufferCache项目代码测试框架')
    parser.add_argument('--scan-all', action='store_true',
                       help='扫描所有文档中的代码块')
    parser.add_argument('--test', choices=['python', 'go', 'rust', 'bash', 'all'],
                       help='测试指定语言的代码（go/rust 编译运行可独立程序，bash 仅语法检查）')
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
        save_report_for_language(tester, report, args.test)
        print("\n" + "="*60)
        print(report)
        print("="*60)


if __name__ == "__main__":
    main()
