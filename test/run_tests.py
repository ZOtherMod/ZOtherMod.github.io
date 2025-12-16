#!/usr/bin/env python3
"""
Test Runner - Run All Tests for Debate Platform
Simple test runner to execute all test suites
"""

import sys
import os
import subprocess
import time

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Print a colored header"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text.center(60)}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}[PASS] {text}{Colors.END}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}[FAIL] {text}{Colors.END}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.END}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}[INFO] {text}{Colors.END}")

def run_test_file(test_file):
    """Run a single test file and return success status"""
    print(f"\n{Colors.PURPLE}[TEST] Running {test_file}...{Colors.END}")
    
    try:
        # Get the directory of this script
        test_dir = os.path.dirname(os.path.abspath(__file__))
        test_path = os.path.join(test_dir, test_file)
        
        if not os.path.exists(test_path):
            print_error(f"Test file not found: {test_file}")
            return False
        
        # Run the test
        result = subprocess.run([sys.executable, test_path], 
                              capture_output=True, text=True, timeout=30)
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        # Check result
        if result.returncode == 0:
            print_success(f"{test_file} completed successfully")
            return True
        else:
            print_error(f"{test_file} failed with exit code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print_error(f"{test_file} timed out after 30 seconds")
        return False
    except Exception as e:
        print_error(f"Error running {test_file}: {e}")
        return False

def check_prerequisites():
    """Check if all required files exist"""
    print_header("CHECKING PREREQUISITES")
    
    required_files = {
        "Database Tests": "test_database.py",
        "Server Tests": "test_server.py", 
        "WebSocket Tests": "test_websocket.py"
    }
    
    missing_files = []
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    for test_name, filename in required_files.items():
        filepath = os.path.join(test_dir, filename)
        if os.path.exists(filepath):
            print_success(f"{test_name}: {filename}")
        else:
            print_error(f"{test_name}: {filename} - NOT FOUND")
            missing_files.append(filename)
    
    # Check backend files
    backend_dir = os.path.join(os.path.dirname(test_dir), 'backend')
    backend_files = ['clean_database.py', 'clean_server.py']
    
    print(f"\n{Colors.BLUE}Backend Files:{Colors.END}")
    for filename in backend_files:
        filepath = os.path.join(backend_dir, filename)
        if os.path.exists(filepath):
            print_success(f"Backend: {filename}")
        else:
            print_error(f"Backend: {filename} - NOT FOUND")
            missing_files.append(f"backend/{filename}")
    
    if missing_files:
        print_warning(f"Missing files: {', '.join(missing_files)}")
        return False
    
    print_success("All required files found")
    return True

def run_all_tests():
    """Run all test suites"""
    print_header("DEBATE PLATFORM TEST SUITE")
    print_info("Starting comprehensive testing...")
    
    # Check prerequisites
    if not check_prerequisites():
        print_error("Prerequisites check failed - cannot run tests")
        return False
    
    # Define test order (database tests first, then server, then websockets)
    test_files = [
        "test_database.py",
        "test_server.py", 
        "test_websocket.py"
    ]
    
    results = {}
    total_tests = len(test_files)
    passed_tests = 0
    
    # Run each test suite
    for test_file in test_files:
        success = run_test_file(test_file)
        results[test_file] = success
        if success:
            passed_tests += 1
        
        # Small delay between tests
        time.sleep(1)
    
    # Print summary
    print_header("TEST SUMMARY")
    
    for test_file, success in results.items():
        status = "PASSED" if success else "FAILED"
        color_func = print_success if success else print_error
        color_func(f"{test_file}: {status}")
    
    print(f"\n{Colors.BOLD}Overall Results:{Colors.END}")
    print(f"Tests Passed: {Colors.GREEN}{passed_tests}{Colors.END}")
    print(f"Tests Failed: {Colors.RED}{total_tests - passed_tests}{Colors.END}")
    print(f"Success Rate: {Colors.CYAN}{(passed_tests/total_tests)*100:.1f}%{Colors.END}")
    
    if passed_tests == total_tests:
        print_success("ALL TESTS PASSED!")
        return True
    else:
        print_warning("Some tests failed - check individual results above")
        return False

def run_individual_test():
    """Run a specific test file"""
    available_tests = {
        "1": ("Database Tests", "test_database.py"),
        "2": ("Server Tests", "test_server.py"),
        "3": ("WebSocket Tests", "test_websocket.py")
    }
    
    print_header("INDIVIDUAL TEST RUNNER")
    
    print("Available tests:")
    for key, (name, filename) in available_tests.items():
        print(f"  {key}. {name} ({filename})")
    
    choice = input(f"\n{Colors.YELLOW}Enter test number (1-3): {Colors.END}").strip()
    
    if choice in available_tests:
        name, filename = available_tests[choice]
        print(f"\n{Colors.BLUE}Running {name}...{Colors.END}")
        success = run_test_file(filename)
        return success
    else:
        print_error("Invalid choice")
        return False

def main():
    """Main test runner"""
    print_header("DEBATE PLATFORM TEST RUNNER")
    
    if len(sys.argv) > 1:
        # Command line argument provided
        if sys.argv[1] == "--all":
            return run_all_tests()
        elif sys.argv[1] == "--database":
            return run_test_file("test_database.py")
        elif sys.argv[1] == "--server":
            return run_test_file("test_server.py")
        elif sys.argv[1] == "--websocket":
            return run_test_file("test_websocket.py")
        else:
            print_error(f"Unknown option: {sys.argv[1]}")
            print_info("Usage: python run_tests.py [--all|--database|--server|--websocket]")
            return False
    else:
        # Interactive mode
        print("Choose test mode:")
        print("  1. Run all tests")
        print("  2. Run individual test")
        print("  3. Check prerequisites only")
        
        choice = input(f"\n{Colors.YELLOW}Enter choice (1-3): {Colors.END}").strip()
        
        if choice == "1":
            return run_all_tests()
        elif choice == "2":
            return run_individual_test()
        elif choice == "3":
            return check_prerequisites()
        else:
            print_error("Invalid choice")
            return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.END}")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
