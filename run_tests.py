#!/usr/bin/env python3
"""Simple test runner for the project."""

import subprocess
import sys
from pathlib import Path


def install_test_dependencies():
    """Install test dependencies if not already installed."""
    print("Installing test dependencies...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "pytest>=7.0.0", "pytest-cov>=4.0.0", "ruff>=0.1.0", "black>=23.0.0"
    ], check=True)


def run_tests():
    """Run the test suite."""
    project_root = Path(__file__).parent
    
    print("Running Pydantic contract tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        str(project_root / "tests" / "test_contracts.py"),
        "-v"
    ], cwd=project_root)
    
    if result.returncode == 0:
        print("✅ Contract tests passed!")
    else:
        print("❌ Contract tests failed!")
        return False
    
    print("\nRunning pipeline smoke tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        str(project_root / "tests" / "test_pipeline_smoke.py"),
        "-v"
    ], cwd=project_root)
    
    if result.returncode == 0:
        print("✅ Pipeline smoke tests passed!")
    else:
        print("❌ Pipeline smoke tests failed!")
        return False
    
    return True


def run_linting():
    """Run code quality checks."""
    project_root = Path(__file__).parent
    
    print("Running ruff linter...")
    result = subprocess.run([
        sys.executable, "-m", "ruff", "check", "src/", "tests/", "streamlit_app/"
    ], cwd=project_root)
    
    if result.returncode == 0:
        print("✅ Linting passed!")
    else:
        print("❌ Linting issues found!")
        return False
    
    return True


def main():
    """Main test runner."""
    print("StAnify Test Suite")
    print("=" * 50)
    
    try:
        # Install dependencies first
        install_test_dependencies()
        
        # Run tests
        tests_passed = run_tests()
        
        # Run linting
        linting_passed = run_linting()
        
        if tests_passed and linting_passed:
            print("\n🎉 All checks passed! Your code is ready!")
            return 0
        else:
            print("\n❌ Some checks failed. Please review the output above.")
            return 1
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running tests: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 1


if __name__ == "__main__":
    sys.exit(main())
