#!/usr/bin/env python3
"""
Network diagnostic script for NANDA agents
This helps debug "Name or service not known" errors
"""

import os
import sys
import socket
import subprocess
import requests
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def test_dns_resolution():
    """Test DNS resolution for common services"""
    print("🔍 Testing DNS Resolution...")
    print("=" * 40)
    
    test_hosts = [
        "google.com",
        "github.com", 
        "anthropic.com",
        "mongodb.net",
        "169.254.169.254"  # EC2 metadata service
    ]
    
    for host in test_hosts:
        try:
            ip = socket.gethostbyname(host)
            print(f"✅ {host} → {ip}")
        except socket.gaierror as e:
            print(f"❌ {host} → {e}")

def test_network_connectivity():
    """Test network connectivity"""
    print("\n🌐 Testing Network Connectivity...")
    print("=" * 40)
    
    test_urls = [
        "https://google.com",
        "https://github.com",
        "https://anthropic.com"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=5)
            print(f"✅ {url} → {response.status_code}")
        except Exception as e:
            print(f"❌ {url} → {e}")

def test_ec2_metadata():
    """Test EC2 metadata service"""
    print("\n☁️  Testing EC2 Metadata Service...")
    print("=" * 40)
    
    try:
        # Test IMDSv2 token
        token_response = requests.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=5
        )
        if token_response.status_code == 200:
            token = token_response.text
            print("✅ IMDSv2 token obtained")
            
            # Test metadata endpoints with token
            endpoints = [
                "instance-id",
                "public-ipv4", 
                "public-hostname",
                "local-ipv4"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(
                        f"http://169.254.169.254/latest/meta-data/{endpoint}",
                        headers={"X-aws-ec2-metadata-token": token},
                        timeout=5
                    )
                    if response.status_code == 200:
                        print(f"✅ {endpoint} → {response.text}")
                    else:
                        print(f"❌ {endpoint} → {response.status_code}")
                except Exception as e:
                    print(f"❌ {endpoint} → {e}")
        else:
            print(f"❌ IMDSv2 token failed: {token_response.status_code}")
            
            # Try IMDSv1 fallback
            print("🔄 Trying IMDSv1 fallback...")
            try:
                response = requests.get(
                    "http://169.254.169.254/latest/meta-data/instance-id",
                    timeout=5
                )
                if response.status_code == 200:
                    print(f"✅ IMDSv1 instance-id → {response.text}")
                else:
                    print(f"❌ IMDSv1 failed: {response.status_code}")
            except Exception as e:
                print(f"❌ IMDSv1 failed: {e}")
                
    except Exception as e:
        print(f"❌ EC2 metadata service unavailable: {e}")
        print("   This is normal if not running on EC2")

def test_port_availability():
    """Test if common ports are available"""
    print("\n🔌 Testing Port Availability...")
    print("=" * 40)
    
    test_ports = [6001, 6002, 6003, 8000, 8080]
    
    for port in test_ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:
                print(f"❌ Port {port} is already in use")
            else:
                print(f"✅ Port {port} is available")
        except Exception as e:
            print(f"⚠️  Port {port} test failed: {e}")
        finally:
            sock.close()

def test_environment_variables():
    """Test environment variables"""
    print("\n🔧 Testing Environment Variables...")
    print("=" * 40)
    
    required_vars = [
        "ANTHROPIC_API_KEY",
        "MONGODB_URI",
        "AGENT_ID"
    ]
    
    optional_vars = [
        "PUBLIC_URL",
        "INTERNAL_HOST", 
        "PORT",
        "DEBUG"
    ]
    
    # Load .env file if exists
    env_file = Path(".env")
    if env_file.exists():
        print("📁 Found .env file")
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        print("✅ Loaded .env file")
    else:
        print("⚠️  No .env file found")
    
    print("\nRequired variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "API_KEY" in var or "URI" in var:
                display_value = f"{'*' * 20} (length: {len(value)})"
            else:
                display_value = value
            print(f"✅ {var} = {display_value}")
        else:
            print(f"❌ {var} = (not set)")
    
    print("\nOptional variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var} = {value}")
        else:
            print(f"⚠️  {var} = (not set)")

def test_nanda_imports():
    """Test NANDA module imports"""
    print("\n📦 Testing NANDA Module Imports...")
    print("=" * 40)
    
    try:
        from nanda_adapter.core.env_loader import load_env_file
        print("✅ env_loader import successful")
        
        from nanda_adapter.simple import SimpleNANDA
        print("✅ SimpleNANDA import successful")
        
        from nanda_adapter.core.network_utils import get_ec2_public_ip, is_ec2_instance
        print("✅ network_utils import successful")
        
        # Test network utils
        print("\n🔍 Testing network detection...")
        is_ec2 = is_ec2_instance()
        print(f"Running on EC2: {is_ec2}")
        
        if is_ec2:
            public_ip = get_ec2_public_ip()
            print(f"EC2 Public IP: {public_ip or 'None'}")
        
    except Exception as e:
        print(f"❌ Import failed: {e}")

def main():
    print("🩺 NANDA Agent Network Diagnostics")
    print("==================================")
    print()
    
    test_dns_resolution()
    test_network_connectivity()
    test_ec2_metadata()
    test_port_availability()
    test_environment_variables()
    test_nanda_imports()
    
    print("\n" + "=" * 50)
    print("🩺 Diagnostic Complete!")
    print("\nIf you see ❌ errors above, those might be causing")
    print("the 'Name or service not known' issue.")

if __name__ == "__main__":
    main()