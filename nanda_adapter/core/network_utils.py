"""
Network utilities for EC2 deployment and auto-detection.

This module provides utilities for detecting EC2 instance networking information
and configuring agents for distributed deployment across cloud instances.
"""

import requests
import socket
from typing import Optional
import os


def get_ec2_public_ip() -> Optional[str]:
    """
    Get the public IP address of the current EC2 instance.
    
    Returns:
        Public IP address string or None if not on EC2 or no public IP
    """
    ip = _get_ec2_metadata('public-ipv4')
    return ip if ip and ip != '' else None


def get_ec2_private_ip() -> Optional[str]:
    """
    Get the private IP address of the current EC2 instance.
    
    Returns:
        Private IP address string or None if not on EC2
    """
    ip = _get_ec2_metadata('local-ipv4')
    return ip if ip and ip != '' else None


def get_ec2_public_hostname() -> Optional[str]:
    """
    Get the public hostname of the current EC2 instance.
    
    Returns:
        Public hostname string or None if not on EC2 or no public hostname
    """
    hostname = _get_ec2_metadata('public-hostname')
    return hostname if hostname and hostname != '' else None


def _get_ec2_metadata_token() -> Optional[str]:
    """
    Get EC2 metadata token for IMDSv2.
    
    Returns:
        Token string or None if not available
    """
    try:
        response = requests.put(
            'http://169.254.169.254/latest/api/token',
            headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'},
            timeout=2
        )
        if response.status_code == 200:
            return response.text.strip()
    except Exception:
        pass
    return None


def _get_ec2_metadata(path: str) -> Optional[str]:
    """
    Get EC2 metadata with IMDSv2 support.
    
    Args:
        path: Metadata path (e.g., 'instance-id', 'public-ipv4')
        
    Returns:
        Metadata value or None if not available
    """
    # Try IMDSv2 first (with token)
    token = _get_ec2_metadata_token()
    if token:
        try:
            response = requests.get(
                f'http://169.254.169.254/latest/meta-data/{path}',
                headers={'X-aws-ec2-metadata-token': token},
                timeout=2
            )
            if response.status_code == 200:
                return response.text.strip()
        except Exception:
            pass
    
    # Fallback to IMDSv1 (without token)
    try:
        response = requests.get(
            f'http://169.254.169.254/latest/meta-data/{path}',
            timeout=2
        )
        if response.status_code == 200:
            return response.text.strip()
    except Exception:
        pass
    
    return None


def get_ec2_instance_id() -> Optional[str]:
    """
    Get the EC2 instance ID.
    
    Returns:
        Instance ID string or None if not on EC2
    """
    return _get_ec2_metadata('instance-id')


def is_ec2_instance() -> bool:
    """
    Check if running on an EC2 instance.
    
    Returns:
        True if running on EC2, False otherwise
    """
    return get_ec2_instance_id() is not None


def get_public_url(port: int, preferred_url: str = None) -> str:
    """
    Get the public URL for this agent, with auto-detection for EC2.
    
    Args:
        port: Port number the agent is running on
        preferred_url: Explicitly set URL (overrides auto-detection)
        
    Returns:
        Complete public URL for the agent
    """
    # If explicitly set and not "auto", use it
    if preferred_url and preferred_url.lower() not in ("auto", ""):
        return preferred_url
    
    # Try to detect EC2 public IP first
    public_ip = get_ec2_public_ip()
    if public_ip:
        print(f"🔍 Detected EC2 public IP: {public_ip}")
        return f"http://{public_ip}:{port}"
    
    # Try to get EC2 public hostname
    public_hostname = get_ec2_public_hostname()
    if public_hostname:
        print(f"🔍 Detected EC2 public hostname: {public_hostname}")
        return f"http://{public_hostname}:{port}"
    
    # Check if we're on EC2 but without public networking
    if is_ec2_instance():
        private_ip = get_ec2_private_ip()
        if private_ip:
            print(f"⚠️  EC2 instance detected but no public IP. Using private IP: {private_ip}")
            print("   Note: Other agents may not be able to reach this instance")
            return f"http://{private_ip}:{port}"
    
    # Fallback to localhost for development
    print("🏠 Using localhost (development mode)")
    return f"http://localhost:{port}"


def test_network_connectivity(target_url: str, timeout: int = 5) -> bool:
    """
    Test if we can reach another agent at the given URL.
    
    Args:
        target_url: URL to test connectivity to
        timeout: Request timeout in seconds
        
    Returns:
        True if agent is reachable, False otherwise
    """
    try:
        # Try to reach the agent's health endpoint
        test_endpoints = [
            f"{target_url}/health",
            f"{target_url}/a2a",
            target_url
        ]
        
        for endpoint in test_endpoints:
            try:
                response = requests.get(endpoint, timeout=timeout)
                if response.status_code in [200, 404]:  # 404 is OK, means server is running
                    return True
            except requests.exceptions.Timeout:
                continue
            except requests.exceptions.ConnectionError:
                continue
        
        return False
        
    except Exception:
        return False


def get_local_ip() -> str:
    """
    Get the local IP address of this machine.
    
    Returns:
        Local IP address string
    """
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def validate_url_format(url: str) -> bool:
    """
    Validate that a URL is properly formatted.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is valid, False otherwise
    """
    if not url:
        return False
    
    # Basic URL validation
    if not (url.startswith('http://') or url.startswith('https://')):
        return False
    
    # Check for valid format
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        return bool(parsed.netloc)
    except Exception:
        return False


def get_network_info() -> dict:
    """
    Get comprehensive network information for debugging.
    
    Returns:
        Dictionary with network information
    """
    info = {
        'is_ec2': is_ec2_instance(),
        'local_ip': get_local_ip(),
        'ec2_public_ip': get_ec2_public_ip(),
        'ec2_private_ip': get_ec2_private_ip(),
        'ec2_public_hostname': get_ec2_public_hostname(),
        'ec2_instance_id': get_ec2_instance_id()
    }
    
    return info


def print_network_debug_info():
    """Print network debugging information."""
    print("\n🌐 Network Configuration Debug Info:")
    print("=" * 50)
    
    info = get_network_info()
    
    print(f"Running on EC2: {'Yes' if info['is_ec2'] else 'No'}")
    print(f"Local IP: {info['local_ip']}")
    
    if info['is_ec2']:
        print(f"EC2 Instance ID: {info['ec2_instance_id']}")
        print(f"EC2 Public IP: {info['ec2_public_ip'] or 'None'}")
        print(f"EC2 Private IP: {info['ec2_private_ip'] or 'None'}")
        print(f"EC2 Public Hostname: {info['ec2_public_hostname'] or 'None'}")
    
    print("=" * 50)