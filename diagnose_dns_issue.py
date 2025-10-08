#!/usr/bin/env python3
"""
Test DNS and network resolution on EC2 to identify the "Name or service not known" issue.
"""

import os
import socket
import subprocess
import platform

def test_dns_and_networking():
    """Test various DNS and networking scenarios."""
    print("🌐 EC2 DNS and Network Diagnostic")
    print("=" * 50)
    
    # Test 1: Basic hostname resolution
    print("\n1️⃣ Testing hostname resolution...")
    try:
        hostname = socket.gethostname()
        print(f"   Hostname: {hostname}")
        
        # Try to resolve our own hostname
        try:
            ip = socket.gethostbyname(hostname)
            print(f"   ✅ Hostname resolves to: {ip}")
        except Exception as e:
            print(f"   ❌ Hostname resolution failed: {e}")
            
    except Exception as e:
        print(f"   ❌ Hostname lookup failed: {e}")
    
    # Test 2: Network interface information
    print("\n2️⃣ Testing network interfaces...")
    try:
        result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
        if result.returncode == 0:
            print("   Network interfaces:")
            for line in result.stdout.split('\n'):
                if 'inet ' in line:
                    print(f"     {line.strip()}")
        else:
            print(f"   ❌ Failed to get network interfaces")
    except Exception as e:
        print(f"   ❌ Network interface check failed: {e}")
    
    # Test 3: /etc/hosts file
    print("\n3️⃣ Testing /etc/hosts...")
    try:
        with open('/etc/hosts', 'r') as f:
            print("   /etc/hosts content:")
            for line in f:
                if line.strip() and not line.startswith('#'):
                    print(f"     {line.strip()}")
    except Exception as e:
        print(f"   ❌ Failed to read /etc/hosts: {e}")
    
    # Test 4: DNS resolution test
    print("\n4️⃣ Testing external DNS resolution...")
    test_hosts = ['google.com', 'github.com', 'anthropic.com']
    for host in test_hosts:
        try:
            ip = socket.gethostbyname(host)
            print(f"   ✅ {host} → {ip}")
        except Exception as e:
            print(f"   ❌ {host} → {e}")
    
    # Test 5: Local binding test
    print("\n5️⃣ Testing port binding...")
    test_ports = [6002, 8000, 8080]
    for port in test_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('0.0.0.0', port))
            sock.close()
            print(f"   ✅ Port {port} binding successful")
        except Exception as e:
            print(f"   ❌ Port {port} binding failed: {e}")
    
    # Test 6: Python-a2a version and internals
    print("\n6️⃣ Testing python-a2a internals...")
    try:
        import python_a2a
        print(f"   python-a2a version: {getattr(python_a2a, '__version__', 'unknown')}")
        
        # Try to inspect what run_server does
        from python_a2a import run_server
        print(f"   run_server function: {run_server}")
        print(f"   run_server module: {run_server.__module__}")
        
        # Check if it's using Flask or FastAPI internally
        try:
            import flask
            print(f"   Flask available: {flask.__version__}")
        except:
            print("   Flask not available")
            
        try:
            import fastapi
            print(f"   FastAPI available: {fastapi.__version__}")
        except:
            print("   FastAPI not available")
            
        try:
            import uvicorn
            print(f"   Uvicorn available: {uvicorn.__version__}")
        except:
            print("   Uvicorn not available")
            
    except Exception as e:
        print(f"   ❌ python-a2a inspection failed: {e}")
    
    # Test 7: Environment variables that might affect networking
    print("\n7️⃣ Checking environment variables...")
    env_vars_to_check = [
        'HOSTNAME', 'HOST', 'INTERNAL_HOST', 'PUBLIC_URL', 
        'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY'
    ]
    for var in env_vars_to_check:
        value = os.environ.get(var)
        if value:
            print(f"   {var} = {value}")
        else:
            print(f"   {var} = (not set)")
    
    # Test 8: Platform information
    print("\n8️⃣ Platform information...")
    print(f"   System: {platform.system()}")
    print(f"   Platform: {platform.platform()}")
    print(f"   Architecture: {platform.architecture()}")
    print(f"   Python: {platform.python_version()}")

if __name__ == "__main__":
    test_dns_and_networking()