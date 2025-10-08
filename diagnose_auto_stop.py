#!/usr/bin/env python3
"""
Server Auto-Stop Diagnostic Tool
================================

This tool checks for common issues that cause servers to stop automatically
on EC2 instances.

Usage:
    python3 diagnose_auto_stop.py agent_d
"""

import os
import sys
import socket
import subprocess
import traceback
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def check_port_conflicts(port):
    """Check if port is already in use"""
    print(f"🔍 Checking port {port} conflicts...")
    
    try:
        # Try to bind to the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        result = sock.bind(('0.0.0.0', port))
        sock.close()
        print(f"   ✅ Port {port} is available")
        return True
    except OSError as e:
        print(f"   ❌ Port {port} conflict: {e}")
        
        # Try to find what's using the port
        try:
            result = subprocess.run(['netstat', '-tulpn'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if f':{port} ' in line:
                    print(f"   📍 Port {port} is used by: {line.strip()}")
        except Exception:
            pass
        
        return False

def check_memory_limits():
    """Check if system has enough memory"""
    print("🔍 Checking memory limits...")
    
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = {}
            for line in f:
                if ':' in line:
                    key, value = line.split(':', 1)
                    meminfo[key.strip()] = value.strip()
        
        mem_total = int(meminfo['MemTotal'].split()[0])  # KB
        mem_available = int(meminfo['MemAvailable'].split()[0])  # KB
        
        mem_total_mb = mem_total // 1024
        mem_available_mb = mem_available // 1024
        
        print(f"   📊 Total memory: {mem_total_mb} MB")
        print(f"   📊 Available memory: {mem_available_mb} MB")
        
        if mem_available_mb < 200:
            print(f"   ⚠️ Low memory warning: Only {mem_available_mb} MB available")
            return False
        elif mem_available_mb < 500:
            print(f"   ⚠️ Memory concern: Only {mem_available_mb} MB available")
        else:
            print(f"   ✅ Memory looks good: {mem_available_mb} MB available")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Could not check memory: {e}")
        return False

def check_disk_space():
    """Check if system has enough disk space"""
    print("🔍 Checking disk space...")
    
    try:
        import shutil
        total, used, free = shutil.disk_usage('/')
        
        free_gb = free // (1024**3)
        total_gb = total // (1024**3)
        used_percent = (used / total) * 100
        
        print(f"   📊 Disk usage: {used_percent:.1f}% used")
        print(f"   📊 Free space: {free_gb} GB of {total_gb} GB")
        
        if free_gb < 1:
            print(f"   ❌ Critical: Only {free_gb} GB free space")
            return False
        elif free_gb < 2:
            print(f"   ⚠️ Warning: Only {free_gb} GB free space") 
        else:
            print(f"   ✅ Disk space looks good")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Could not check disk space: {e}")
        return False

def check_python_environment():
    """Check Python environment and dependencies"""
    print("🔍 Checking Python environment...")
    
    # Check Python version
    print(f"   🐍 Python version: {sys.version}")
    
    # Check critical imports
    critical_imports = [
        ('anthropic', 'Anthropic API client'),
        ('python_a2a', 'A2A protocol library'),
        ('flask', 'Web server framework'),
        ('requests', 'HTTP client library')
    ]
    
    missing_imports = []
    for module, description in critical_imports:
        try:
            __import__(module)
            print(f"   ✅ {module} ({description})")
        except ImportError:
            print(f"   ❌ {module} ({description}) - MISSING")
            missing_imports.append(module)
    
    if missing_imports:
        print(f"   ⚠️ Missing dependencies: {', '.join(missing_imports)}")
        return False
    
    return True

def check_environment_variables():
    """Check required environment variables"""
    print("🔍 Checking environment variables...")
    
    required_vars = {
        'ANTHROPIC_API_KEY': 'Anthropic API key for Claude',
    }
    
    optional_vars = {
        'PORT': 'Server port (defaults to 6000)',
        'INTERNAL_HOST': 'Internal host binding (defaults to 0.0.0.0)',
        'PUBLIC_URL': 'Public URL for registration (auto-detected if not set)',
        'MONGODB_URI': 'MongoDB connection string (optional)',
    }
    
    missing_required = []
    
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            masked_value = value[:10] + '...' if len(value) > 10 else value
            print(f"   ✅ {var}: {masked_value} ({desc})")
        else:
            print(f"   ❌ {var}: NOT SET ({desc})")
            missing_required.append(var)
    
    for var, desc in optional_vars.items():
        value = os.getenv(var, 'NOT SET')
        print(f"   📋 {var}: {value} ({desc})")
    
    if missing_required:
        print(f"   ⚠️ Missing required variables: {', '.join(missing_required)}")
        return False
    
    return True

def check_process_limits():
    """Check process and file descriptor limits"""
    print("🔍 Checking process limits...")
    
    try:
        import resource
        
        # Check file descriptor limits
        soft_fd, hard_fd = resource.getrlimit(resource.RLIMIT_NOFILE)
        print(f"   📊 File descriptors: {soft_fd} soft limit, {hard_fd} hard limit")
        
        if soft_fd < 1024:
            print(f"   ⚠️ Low file descriptor limit: {soft_fd}")
        else:
            print(f"   ✅ File descriptor limit looks good")
        
        # Check process limits
        soft_proc, hard_proc = resource.getrlimit(resource.RLIMIT_NPROC)
        print(f"   📊 Processes: {soft_proc} soft limit, {hard_proc} hard limit")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Could not check process limits: {e}")
        return False

def check_network_connectivity():
    """Check network connectivity"""
    print("🔍 Checking network connectivity...")
    
    try:
        # Try to resolve DNS
        socket.gethostbyname('google.com')
        print("   ✅ DNS resolution working")
        
        # Try to make HTTP request
        import urllib.request
        urllib.request.urlopen('https://httpbin.org/get', timeout=10)
        print("   ✅ Outbound HTTP requests working")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Network connectivity issue: {e}")
        return False

def run_quick_server_test(agent_id, port):
    """Run a quick server startup test"""
    print(f"🔍 Running quick server test for {agent_id}...")
    
    try:
        # Set port environment variable
        os.environ['PORT'] = str(port)
        
        # Try to import and create agent
        from nanda_adapter.simple import SimpleNANDA
        
        agent = SimpleNANDA(
            agent_id=f"test_{agent_id}",
            service_charge=0,  # Free for testing
            require_anthropic=False  # Don't require Claude for test
        )
        
        print(f"   ✅ Agent creation successful")
        print(f"   📋 Public URL: {agent.public_url}")
        print(f"   📋 Internal bind: {agent.internal_host}:{agent.port}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Agent creation failed: {e}")
        traceback.print_exc()
        return False

def main():
    agent_id = sys.argv[1] if len(sys.argv) > 1 else "agent_d"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6002
    
    print("🔍 Server Auto-Stop Diagnostic Tool")
    print("===================================")
    print(f"Agent ID: {agent_id}")
    print(f"Port: {port}")
    print(f"Working directory: {os.getcwd()}")
    print()
    
    checks = [
        ("Port conflicts", lambda: check_port_conflicts(port)),
        ("Memory limits", check_memory_limits),
        ("Disk space", check_disk_space),
        ("Python environment", check_python_environment),
        ("Environment variables", check_environment_variables),
        ("Process limits", check_process_limits),
        ("Network connectivity", check_network_connectivity),
        ("Quick server test", lambda: run_quick_server_test(agent_id, port)),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, check_func in checks:
        print(f"\n{'='*50}")
        try:
            if check_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {check_name} check failed with exception: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print("📊 DIAGNOSTIC SUMMARY")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All checks passed! The server should start normally.")
        print("If it's still auto-stopping, run with the persistent monitor:")
        print(f"   python3 persistent_server_monitor.py {agent_id} --port {port}")
    else:
        print(f"\n⚠️ {failed} issues found that may cause auto-stopping.")
        print("Fix the issues above before starting the server.")
    
    return failed

if __name__ == "__main__":
    sys.exit(main())