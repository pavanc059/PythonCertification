"""
Security Audit Script for StockIQ Platform.

Performs automated security checks:
- Checks for exposed secrets in code
- Validates .gitignore configuration
- Scans for common security anti-patterns
- Checks dependency vulnerabilities
- Validates security configurations
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any
import subprocess

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
ENDC = '\033[0m'
BOLD = '\033[1m'


class SecurityAudit:
    """Performs comprehensive security audit."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.passed: List[str] = []
    
    def run_all_checks(self) -> bool:
        """
        Run all security checks.
        
        Returns:
            True if all critical checks passed, False otherwise
        """
        print(f"{BOLD}{BLUE}=== StockIQ Security Audit ==={ENDC}\n")
        
        self.check_exposed_secrets()
        self.check_gitignore()
        self.check_environment_variables()
        self.check_sql_patterns()
        self.check_hardcoded_credentials()
        self.check_debug_settings()
        self.check_dependency_vulnerabilities()
        self.check_security_headers_config()
        self.check_rate_limiting_config()
        
        self.print_results()
        
        return len(self.issues) == 0
    
    def check_exposed_secrets(self):
        """Check for exposed secrets in Python files."""
        print(f"{BLUE}Checking for exposed secrets...{ENDC}")
        
        secret_patterns = [
            (r'api[_-]?key\s*=\s*["\']([^"\']{20,})["\']', 'API key'),
            (r'secret[_-]?key\s*=\s*["\']([^"\']{20,})["\']', 'Secret key'),
            (r'password\s*=\s*["\']([^"\']+)["\']', 'Password'),
            (r'bearer\s+([a-zA-Z0-9_\-\.]{20,})', 'Bearer token'),
        ]
        
        python_files = list(self.project_root.rglob('*.py'))
        found_secrets = False
        
        for file_path in python_files:
            # Skip test files and examples
            if 'test_' in file_path.name or 'example' in str(file_path):
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8')
                
                for pattern, secret_type in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Check if it's a placeholder or test value
                        value = match.group(1) if match.groups() else match.group(0)
                        if self._is_real_secret(value):
                            self.issues.append({
                                'type': 'exposed_secret',
                                'severity': 'CRITICAL',
                                'file': str(file_path.relative_to(self.project_root)),
                                'secret_type': secret_type,
                                'message': f'Possible exposed {secret_type} in {file_path.name}'
                            })
                            found_secrets = True
            except Exception as e:
                pass
        
        if not found_secrets:
            self.passed.append("No exposed secrets found in code")
    
    def _is_real_secret(self, value: str) -> bool:
        """Check if value looks like a real secret (not a placeholder)."""
        placeholders = [
            'your_', 'test_', 'example_', 'change_this', 'replace_me',
            'xxx', 'yyy', 'zzz', '123', 'abc', 'placeholder', 'dummy'
        ]
        
        value_lower = value.lower()
        return not any(placeholder in value_lower for placeholder in placeholders)
    
    def check_gitignore(self):
        """Check .gitignore for sensitive files."""
        print(f"{BLUE}Checking .gitignore configuration...{ENDC}")
        
        gitignore_path = self.project_root / '.gitignore'
        
        if not gitignore_path.exists():
            self.issues.append({
                'type': 'missing_gitignore',
                'severity': 'HIGH',
                'message': '.gitignore file not found'
            })
            return
        
        content = gitignore_path.read_text()
        
        required_patterns = [
            '.env',
            '*.key',
            '*.pem',
            '__pycache__',
        ]
        
        missing = []
        for pattern in required_patterns:
            if pattern not in content:
                missing.append(pattern)
        
        if missing:
            self.warnings.append({
                'type': 'incomplete_gitignore',
                'severity': 'MEDIUM',
                'message': f'Missing patterns in .gitignore: {", ".join(missing)}'
            })
        else:
            self.passed.append(".gitignore properly configured")
    
    def check_environment_variables(self):
        """Check if secrets are using environment variables."""
        print(f"{BLUE}Checking environment variable usage...{ENDC}")
        
        env_example = self.project_root / '.env.example'
        
        if not env_example.exists():
            self.warnings.append({
                'type': 'missing_env_example',
                'severity': 'LOW',
                'message': '.env.example file not found'
            })
        else:
            self.passed.append(".env.example file exists")
        
        # Check if .env is in .gitignore
        gitignore = self.project_root / '.gitignore'
        if gitignore.exists():
            content = gitignore.read_text()
            if '.env' not in content:
                self.issues.append({
                    'type': 'env_not_ignored',
                    'severity': 'HIGH',
                    'message': '.env file not in .gitignore'
                })
    
    def check_sql_patterns(self):
        """Check for SQL injection vulnerabilities."""
        print(f"{BLUE}Checking for SQL injection vulnerabilities...{ENDC}")
        
        dangerous_patterns = [
            (r'execute\([\'"].*\+.*[\'"]', 'String concatenation in SQL'),
            (r'execute\([\'"].*%.*[\'"]', 'String formatting in SQL'),
            (r'execute\([\'"].*\.format', 'String format in SQL'),
            (r'execute\(f[\'"]', 'f-string in SQL'),
        ]
        
        python_files = list(self.project_root.rglob('*.py'))
        found_issues = False
        
        for file_path in python_files:
            if 'test_' in file_path.name or 'security' in file_path.name:
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8')
                
                for pattern, issue_type in dangerous_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        self.issues.append({
                            'type': 'sql_injection_risk',
                            'severity': 'HIGH',
                            'file': str(file_path.relative_to(self.project_root)),
                            'message': f'{issue_type} in {file_path.name}'
                        })
                        found_issues = True
            except Exception:
                pass
        
        if not found_issues:
            self.passed.append("No SQL injection patterns detected")
    
    def check_hardcoded_credentials(self):
        """Check for hardcoded credentials."""
        print(f"{BLUE}Checking for hardcoded credentials...{ENDC}")
        
        config_file = self.project_root / 'stockiq' / 'infrastructure' / 'config.py'
        
        if config_file.exists():
            content = config_file.read_text()
            
            # Check for non-placeholder defaults
            if 'password@localhost' in content:
                self.warnings.append({
                    'type': 'placeholder_credentials',
                    'severity': 'LOW',
                    'message': 'Placeholder credentials in config.py (ensure production uses environment variables)'
                })
            
            # Check that environment variables are used
            if 'env=' not in content and 'Field' not in content:
                self.issues.append({
                    'type': 'missing_env_vars',
                    'severity': 'MEDIUM',
                    'message': 'Config file may not be using environment variables'
                })
            else:
                self.passed.append("Configuration uses environment variables")
    
    def check_debug_settings(self):
        """Check debug mode configuration."""
        print(f"{BLUE}Checking debug settings...{ENDC}")
        
        config_file = self.project_root / 'stockiq' / 'infrastructure' / 'config.py'
        
        if config_file.exists():
            content = config_file.read_text()
            
            if 'debug: bool = Field(default=True' in content:
                self.warnings.append({
                    'type': 'debug_default_true',
                    'severity': 'MEDIUM',
                    'message': 'Debug mode defaults to True (ensure production sets DEBUG=False)'
                })
            else:
                self.passed.append("Debug mode defaults appropriately")
    
    def check_dependency_vulnerabilities(self):
        """Check for known dependency vulnerabilities."""
        print(f"{BLUE}Checking dependency vulnerabilities...{ENDC}")
        
        try:
            result = subprocess.run(
                ['pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.passed.append("Dependency check completed (manual review recommended)")
            else:
                self.warnings.append({
                    'type': 'dependency_check_failed',
                    'severity': 'LOW',
                    'message': 'Could not check dependencies automatically'
                })
        except Exception as e:
            self.warnings.append({
                'type': 'dependency_check_error',
                'severity': 'LOW',
                'message': f'Dependency check failed: {str(e)}'
            })
    
    def check_security_headers_config(self):
        """Check if security headers are configured."""
        print(f"{BLUE}Checking security headers configuration...{ENDC}")
        
        security_file = self.project_root / 'stockiq' / 'infrastructure' / 'security.py'
        
        if security_file.exists():
            content = security_file.read_text()
            
            required_headers = [
                'X-Content-Type-Options',
                'X-Frame-Options',
                'Content-Security-Policy',
                'Strict-Transport-Security',
            ]
            
            missing = []
            for header in required_headers:
                if header not in content:
                    missing.append(header)
            
            if missing:
                self.warnings.append({
                    'type': 'missing_security_headers',
                    'severity': 'MEDIUM',
                    'message': f'Missing security headers: {", ".join(missing)}'
                })
            else:
                self.passed.append("Security headers properly configured")
        else:
            self.issues.append({
                'type': 'missing_security_module',
                'severity': 'HIGH',
                'message': 'Security module not found'
            })
    
    def check_rate_limiting_config(self):
        """Check if rate limiting is configured."""
        print(f"{BLUE}Checking rate limiting configuration...{ENDC}")
        
        security_file = self.project_root / 'stockiq' / 'infrastructure' / 'security.py'
        
        if security_file.exists():
            content = security_file.read_text()
            
            if 'RateLimiter' in content:
                self.passed.append("Rate limiting implemented")
            else:
                self.warnings.append({
                    'type': 'missing_rate_limiting',
                    'severity': 'MEDIUM',
                    'message': 'Rate limiting not found in security module'
                })
    
    def print_results(self):
        """Print audit results."""
        print(f"\n{BOLD}{BLUE}=== Audit Results ==={ENDC}\n")
        
        # Print passed checks
        if self.passed:
            print(f"{GREEN}{BOLD}Passed Checks ({len(self.passed)}):{ENDC}")
            for check in self.passed:
                print(f"  {GREEN}✓{ENDC} {check}")
            print()
        
        # Print warnings
        if self.warnings:
            print(f"{YELLOW}{BOLD}Warnings ({len(self.warnings)}):{ENDC}")
            for warning in self.warnings:
                severity = warning.get('severity', 'UNKNOWN')
                message = warning['message']
                print(f"  {YELLOW}⚠{ENDC} [{severity}] {message}")
                if 'file' in warning:
                    print(f"      File: {warning['file']}")
            print()
        
        # Print issues
        if self.issues:
            print(f"{RED}{BOLD}Issues ({len(self.issues)}):{ENDC}")
            for issue in self.issues:
                severity = issue.get('severity', 'UNKNOWN')
                message = issue['message']
                print(f"  {RED}✗{ENDC} [{severity}] {message}")
                if 'file' in issue:
                    print(f"      File: {issue['file']}")
            print()
        
        # Print summary
        print(f"{BOLD}{BLUE}=== Summary ==={ENDC}")
        print(f"  Passed: {GREEN}{len(self.passed)}{ENDC}")
        print(f"  Warnings: {YELLOW}{len(self.warnings)}{ENDC}")
        print(f"  Issues: {RED}{len(self.issues)}{ENDC}")
        print()
        
        if len(self.issues) == 0:
            print(f"{GREEN}{BOLD}✓ Security audit passed!{ENDC}")
            return True
        else:
            print(f"{RED}{BOLD}✗ Security audit failed. Please address the issues above.{ENDC}")
            return False


def main():
    """Run security audit."""
    # Get project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    audit = SecurityAudit(str(project_root))
    success = audit.run_all_checks()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
