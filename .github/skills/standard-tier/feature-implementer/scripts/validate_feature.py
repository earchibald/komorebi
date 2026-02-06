#!/usr/bin/env python3
"""
Feature Validation Script for Komorebi

Validates that feature implementation follows project conventions:
- Type hints on all functions
- Async/await patterns
- No hardcoded secrets
- Proper Pydantic schema patterns
- Import organization

Usage:
    python validate_feature.py <file_path>

Example:
    python validate_feature.py backend/app/api/chunks.py
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import NamedTuple


class ValidationResult(NamedTuple):
    passed: bool
    message: str
    line: int | None = None


class FeatureValidator:
    """Validates Python files against Komorebi conventions."""

    # Patterns for secret detection
    SECRET_PATTERNS = [
        (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Personal Access Token'),
        (r'sk_live_[a-zA-Z0-9]+', 'Stripe Live Key'),
        (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API Key'),
        (r'ANTHROPIC_API_KEY\s*=\s*["\'][^"\']+["\']', 'Anthropic API Key'),
        (r'AKIA[A-Z0-9]{16}', 'AWS Access Key'),
        (r'aws_secret_access_key\s*=\s*["\'][^"\']+["\']', 'AWS Secret Key'),
        (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
        (r'secret\s*=\s*["\'][^"\']+["\']', 'Hardcoded secret'),
    ]
    
    # TODO patterns
    TODO_PATTERN = re.compile(r'#\s*TODO[:\s]', re.IGNORECASE)

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = file_path.read_text()
        self.lines = self.content.split('\n')
        try:
            self.tree = ast.parse(self.content)
        except SyntaxError as e:
            print(f"❌ Syntax error in {file_path}: {e}")
            sys.exit(1)

    def validate_all(self) -> list[ValidationResult]:
        """Run all validation checks."""
        results = []
        
        # Check for secrets
        results.extend(self.check_secrets())
        
        # Check for incomplete TODOs
        results.extend(self.check_todos())
        
        # Check type hints
        results.extend(self.check_type_hints())
        
        # Check async patterns
        results.extend(self.check_async_patterns())
        
        # Check import organization
        results.extend(self.check_imports())
        
        return results

    def check_secrets(self) -> list[ValidationResult]:
        """Check for hardcoded secrets."""
        results = []
        
        for pattern, name in self.SECRET_PATTERNS:
            for i, line in enumerate(self.lines, 1):
                if re.search(pattern, line):
                    results.append(ValidationResult(
                        passed=False,
                        message=f"Potential {name} detected",
                        line=i
                    ))
        
        if not results:
            results.append(ValidationResult(
                passed=True,
                message="No hardcoded secrets detected"
            ))
        
        return results

    def check_todos(self) -> list[ValidationResult]:
        """Check for incomplete TODO comments."""
        results = []
        
        for i, line in enumerate(self.lines, 1):
            if self.TODO_PATTERN.search(line):
                # Allow specific scaffold TODOs
                if 'TODO: Add your custom' in line or 'TODO: Implement' in line:
                    continue
                results.append(ValidationResult(
                    passed=False,
                    message="Incomplete TODO comment",
                    line=i
                ))
        
        if not results:
            results.append(ValidationResult(
                passed=True,
                message="No incomplete TODO comments"
            ))
        
        return results

    def check_type_hints(self) -> list[ValidationResult]:
        """Check that all functions have type hints."""
        results = []
        
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip private/dunder methods for now
                if node.name.startswith('__') and node.name.endswith('__'):
                    continue
                if node.name.startswith('_'):
                    continue
                
                # Check return type
                if node.returns is None:
                    results.append(ValidationResult(
                        passed=False,
                        message=f"Function '{node.name}' missing return type hint",
                        line=node.lineno
                    ))
                
                # Check parameter type hints (skip self, cls)
                for arg in node.args.args:
                    if arg.arg in ('self', 'cls'):
                        continue
                    if arg.annotation is None:
                        results.append(ValidationResult(
                            passed=False,
                            message=f"Parameter '{arg.arg}' in '{node.name}' missing type hint",
                            line=node.lineno
                        ))
        
        if not results:
            results.append(ValidationResult(
                passed=True,
                message="All functions have type hints"
            ))
        
        return results

    def check_async_patterns(self) -> list[ValidationResult]:
        """Check async/await patterns."""
        results = []
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                # Check for FastAPI decorators on sync functions
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Attribute):
                        if decorator.attr in ('get', 'post', 'put', 'patch', 'delete'):
                            results.append(ValidationResult(
                                passed=False,
                                message=f"Router endpoint '{node.name}' should be async",
                                line=node.lineno
                            ))
        
        # Check for missing await (basic check)
        for i, line in enumerate(self.lines, 1):
            # Check for session.execute without await
            if 'session.execute(' in line and 'await' not in line:
                results.append(ValidationResult(
                    passed=False,
                    message="Database query may be missing 'await'",
                    line=i
                ))
            
            # Check for repo methods without await
            if re.search(r'\brepo\.\w+\(', line) and 'await' not in line and 'async' not in line:
                # Skip if it's a definition
                if 'def ' not in line and '= repo.' not in line:
                    continue
                if '= repo.' in line and 'await' not in line:
                    results.append(ValidationResult(
                        passed=False,
                        message="Repository method may be missing 'await'",
                        line=i
                    ))
        
        if not results:
            results.append(ValidationResult(
                passed=True,
                message="Async patterns look correct"
            ))
        
        return results

    def check_imports(self) -> list[ValidationResult]:
        """Check import organization (basic)."""
        results = []
        
        # Get all import statements
        imports = []
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(node)
        
        # Check for duplicate imports
        seen_imports = set()
        for node in imports:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in seen_imports:
                        results.append(ValidationResult(
                            passed=False,
                            message=f"Duplicate import: {alias.name}",
                            line=node.lineno
                        ))
                    seen_imports.add(alias.name)
        
        if not results:
            results.append(ValidationResult(
                passed=True,
                message="Imports look organized"
            ))
        
        return results


def print_results(results: list[ValidationResult], file_path: Path) -> int:
    """Print validation results and return exit code."""
    print(f"\n📋 Validation Results for {file_path}")
    print("=" * 60)
    
    passed = []
    failed = []
    
    for result in results:
        if result.passed:
            passed.append(result)
        else:
            failed.append(result)
    
    # Print failures first
    if failed:
        print("\n❌ Issues Found:")
        for result in failed:
            line_info = f" (line {result.line})" if result.line else ""
            print(f"   • {result.message}{line_info}")
    
    # Print passes
    if passed:
        print("\n✅ Checks Passed:")
        for result in passed:
            print(f"   • {result.message}")
    
    print()
    print("=" * 60)
    
    if failed:
        print(f"❌ VALIDATION FAILED: {len(failed)} issue(s) found")
        return 1
    else:
        print("✅ VALIDATION PASSED: All checks passed")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate feature implementation against Komorebi conventions"
    )
    parser.add_argument(
        "file_path",
        help="Path to the Python file to validate"
    )
    
    args = parser.parse_args()
    file_path = Path(args.file_path)
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    if not file_path.suffix == '.py':
        print(f"❌ Not a Python file: {file_path}")
        sys.exit(1)
    
    validator = FeatureValidator(file_path)
    results = validator.validate_all()
    exit_code = print_results(results, file_path)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
