#!/usr/bin/env python3
"""
Quality Audit Script for Antika Auction Watcher
Validates implementation against rules.yaml requirements
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print a colored header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")

def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}? {text}{Colors.END}")

def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}? {text}{Colors.END}")

def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}? {text}{Colors.END}")

def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}? {text}{Colors.END}")

def get_python_files(root_dir: str, exclude_dirs: List[str] = None) -> List[Path]:
    """Get all Python files in directory."""
    if exclude_dirs is None:
        exclude_dirs = ['__pycache__', '.pytest_cache', 'venv', 'env', '.git']
    
    python_files = []
    root_path = Path(root_dir)
    
    for py_file in root_path.rglob('*.py'):
        if not any(ex in str(py_file) for ex in exclude_dirs):
            python_files.append(py_file)
    
    return python_files

def check_unused_imports(file_path: Path) -> List[str]:
    """Check for unused imports in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # Get all imports
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        
        # Check usage (simple check)
        unused = []
        for imp in imports:
            # Skip common imports that might be used indirectly
            if imp in ['typing', 'abc', 'enum', '__future__']:
                continue
            
            # Simple usage check (not perfect but good enough)
            pattern = r'\b' + re.escape(imp) + r'\b'
            occurrences = len(re.findall(pattern, content))
            
            # If only appears once (the import itself), it might be unused
            if occurrences <= 1:
                unused.append(imp)
        
        return unused
    except Exception as e:
        return []

def check_file_size(file_path: Path, max_lines: int = 500) -> Tuple[int, bool]:
    """Check if file exceeds maximum lines."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = len(f.readlines())
        return lines, lines > max_lines
    except Exception:
        return 0, False

def check_naming_conventions(file_path: Path) -> List[str]:
    """Check naming conventions (snake_case for functions, PascalCase for classes)."""
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check function names (should be snake_case)
                if not node.name.startswith('_') and not node.name.islower():
                    if node.name != node.name.lower().replace(' ', '_'):
                        issues.append(f"Function '{node.name}' not in snake_case")
            
            elif isinstance(node, ast.ClassDef):
                # Check class names (should be PascalCase)
                if not node.name[0].isupper():
                    issues.append(f"Class '{node.name}' not in PascalCase")
    
    except Exception:
        pass
    
    return issues

def check_dead_code(file_path: Path) -> int:
    """Check for commented code blocks."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        comment_block_size = 0
        max_comment_block = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#') and len(stripped) > 3:
                comment_block_size += 1
            else:
                if comment_block_size > max_comment_block:
                    max_comment_block = comment_block_size
                comment_block_size = 0
        
        return max_comment_block
    except Exception:
        return 0

def check_security_rules(root_dir: str) -> Dict[str, bool]:
    """Check security rules compliance."""
    results = {
        'jwt_secret_env': False,
        'password_hashing': False,
        'encryption_used': False,
        'no_hardcoded_secrets': True
    }
    
    python_files = get_python_files(root_dir)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for JWT secret from environment
            if 'jwt_secret' in content.lower() and 'settings.' in content:
                results['jwt_secret_env'] = True
            
            # Check for bcrypt usage
            if 'bcrypt' in content or 'pwd_context' in content:
                results['password_hashing'] = True
            
            # Check for encryption
            if 'Fernet' in content or 'encrypt' in content.lower():
                results['encryption_used'] = True
            
            # Check for hardcoded secrets (common patterns)
            hardcoded_patterns = [
                r'password\s*=\s*["\'][^"\']{8,}["\']',
                r'secret\s*=\s*["\'][^"\']{16,}["\']',
                r'api_key\s*=\s*["\'][^"\']{16,}["\']'
            ]
            
            for pattern in hardcoded_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    # Exclude example or test values
                    if 'example' not in content.lower() and 'test' not in str(file_path).lower():
                        results['no_hardcoded_secrets'] = False
        
        except Exception:
            pass
    
    return results

def check_required_files(root_dir: str) -> Dict[str, bool]:
    """Check if required files exist."""
    required_files = {
        'docker-compose.yml': False,
        '.env.example': False,
        'Makefile': False,
        'backend/requirements.txt': False,
        'README.md': False
    }
    
    root_path = Path(root_dir).parent  # Go up to workspace root
    
    for file_name in required_files:
        file_path = root_path / file_name
        required_files[file_name] = file_path.exists()
    
    return required_files

def check_required_directories(root_dir: str) -> Dict[str, bool]:
    """Check if required directories exist."""
    required_dirs = {
        'backend/core': False,
        'backend/db': False,
        'backend/services': False,
        'backend/realtime': False,
        'backend/routers': False
    }
    
    root_path = Path(root_dir).parent
    
    for dir_name in required_dirs:
        dir_path = root_path / dir_name
        required_dirs[dir_name] = dir_path.exists() and dir_path.is_dir()
    
    return required_dirs

def check_async_usage(root_dir: str) -> Tuple[int, int]:
    """Check async/await usage in I/O operations."""
    async_count = 0
    total_io_funcs = 0
    
    python_files = get_python_files(root_dir)
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_str = ast.unparse(node) if hasattr(ast, 'unparse') else ''
                    
                    # Check if function does I/O
                    is_io = any(keyword in func_str.lower() for keyword in 
                               ['session', 'database', 'redis', 'http', 'request'])
                    
                    if is_io:
                        total_io_funcs += 1
                        if isinstance(node, ast.AsyncFunctionDef):
                            async_count += 1
        
        except Exception:
            pass
    
    return async_count, total_io_funcs

def analyze_codebase(root_dir: str):
    """Perform comprehensive code analysis."""
    print_header("ANTIKA AUCTION WATCHER - QUALITY AUDIT")
    
    python_files = get_python_files(root_dir)
    
    # Statistics
    total_files = len(python_files)
    total_lines = 0
    issues_found = 0
    
    print_info(f"Analyzing {total_files} Python files...")
    
    # 1. FILE SIZE CHECK
    print_header("?? FILE SIZE COMPLIANCE (Max 500 lines)")
    oversized_files = []
    large_files = []
    
    for file_path in python_files:
        lines, exceeds = check_file_size(file_path, max_lines=500)
        total_lines += lines
        
        if exceeds:
            oversized_files.append((file_path, lines))
            issues_found += 1
        elif lines > 400:
            large_files.append((file_path, lines))
    
    if oversized_files:
        print_error(f"Found {len(oversized_files)} files exceeding 500 lines:")
        for file_path, lines in oversized_files:
            print(f"  - {file_path.relative_to(Path(root_dir).parent)}: {lines} lines")
    else:
        print_success("All files are within size limits (< 500 lines)")
    
    if large_files:
        print_warning(f"Found {len(large_files)} files over 400 lines (consider refactoring):")
        for file_path, lines in large_files:
            print(f"  - {file_path.relative_to(Path(root_dir).parent)}: {lines} lines")
    
    # 2. NAMING CONVENTIONS
    print_header("?? NAMING CONVENTIONS (snake_case / PascalCase)")
    naming_issues = []
    
    for file_path in python_files:
        issues = check_naming_conventions(file_path)
        if issues:
            naming_issues.extend([(file_path, issue) for issue in issues])
    
    if naming_issues:
        print_warning(f"Found {len(naming_issues)} naming convention issues:")
        for file_path, issue in naming_issues[:10]:  # Show first 10
            print(f"  - {file_path.name}: {issue}")
        if len(naming_issues) > 10:
            print(f"  ... and {len(naming_issues) - 10} more")
    else:
        print_success("All functions and classes follow naming conventions")
    
    # 3. DEAD CODE CHECK
    print_header("???  DEAD CODE CHECK (Comment blocks > 5 lines)")
    dead_code_files = []
    
    for file_path in python_files:
        max_block = check_dead_code(file_path)
        if max_block > 5:
            dead_code_files.append((file_path, max_block))
            issues_found += 1
    
    if dead_code_files:
        print_warning(f"Found {len(dead_code_files)} files with large comment blocks:")
        for file_path, size in dead_code_files:
            print(f"  - {file_path.relative_to(Path(root_dir).parent)}: {size} lines")
    else:
        print_success("No large commented code blocks found")
    
    # 4. SECURITY RULES
    print_header("?? SECURITY RULES COMPLIANCE")
    security_results = check_security_rules(root_dir)
    
    security_rules = {
        'jwt_secret_env': 'JWT secret loaded from environment',
        'password_hashing': 'Password hashing (bcrypt) implemented',
        'encryption_used': 'Encryption for sensitive data',
        'no_hardcoded_secrets': 'No hardcoded secrets found'
    }
    
    for rule, description in security_rules.items():
        if security_results[rule]:
            print_success(description)
        else:
            print_error(description)
            issues_found += 1
    
    # 5. REQUIRED FILES
    print_header("?? REQUIRED FILES")
    required_files = check_required_files(root_dir)
    
    for file_name, exists in required_files.items():
        if exists:
            print_success(f"{file_name}")
        else:
            print_error(f"{file_name} - MISSING")
            issues_found += 1
    
    # 6. REQUIRED DIRECTORIES
    print_header("?? REQUIRED DIRECTORY STRUCTURE")
    required_dirs = check_required_directories(root_dir)
    
    for dir_name, exists in required_dirs.items():
        if exists:
            print_success(f"{dir_name}/")
        else:
            print_error(f"{dir_name}/ - MISSING")
            issues_found += 1
    
    # 7. ASYNC I/O USAGE
    print_header("? ASYNC I/O USAGE")
    async_count, total_io = check_async_usage(root_dir)
    
    if total_io > 0:
        percentage = (async_count / total_io) * 100
        print_info(f"I/O functions using async: {async_count}/{total_io} ({percentage:.1f}%)")
        
        if percentage >= 80:
            print_success("Excellent async adoption for I/O operations")
        elif percentage >= 50:
            print_warning("Good async usage, but could be improved")
        else:
            print_warning("Consider converting more I/O operations to async")
    
    # 8. CODE STATISTICS
    print_header("?? CODE STATISTICS")
    print_info(f"Total Python files: {total_files}")
    print_info(f"Total lines of code: {total_lines:,}")
    print_info(f"Average file size: {total_lines // total_files if total_files > 0 else 0} lines")
    
    # Calculate files by size category
    small_files = sum(1 for f in python_files if check_file_size(f, 100)[0] < 100)
    medium_files = sum(1 for f in python_files if 100 <= check_file_size(f, 300)[0] < 300)
    large_files_count = sum(1 for f in python_files if check_file_size(f, 500)[0] >= 300)
    
    print_info(f"Files by size: Small (<100): {small_files}, Medium (100-300): {medium_files}, Large (>300): {large_files_count}")
    
    # 9. FINAL SCORE
    print_header("?? QUALITY SCORE")
    
    max_issues = 50  # Arbitrary max for scoring
    score = max(0, 100 - (issues_found * 5))
    
    if score >= 90:
        color = Colors.GREEN
        grade = "A (Excellent)"
    elif score >= 80:
        color = Colors.CYAN
        grade = "B (Good)"
    elif score >= 70:
        color = Colors.YELLOW
        grade = "C (Fair)"
    else:
        color = Colors.RED
        grade = "D (Needs Improvement)"
    
    print(f"{Colors.BOLD}Quality Score: {color}{score}/100{Colors.END}")
    print(f"{Colors.BOLD}Grade: {color}{grade}{Colors.END}")
    print(f"\n{Colors.BOLD}Issues Found: {Colors.RED if issues_found > 0 else Colors.GREEN}{issues_found}{Colors.END}")
    
    if issues_found == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}?? PERFECT! No issues found!{Colors.END}")
    elif issues_found < 5:
        print(f"\n{Colors.CYAN}{Colors.BOLD}? Great job! Only minor issues found.{Colors.END}")
    elif issues_found < 10:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}?? Good work! Some improvements recommended.{Colors.END}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}??  Several issues found. Please review and fix.{Colors.END}")
    
    print("\n" + "="*70 + "\n")
    
    return issues_found == 0

if __name__ == "__main__":
    # Get the backend directory
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    
    # Run the audit
    success = analyze_codebase(str(backend_dir))
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
