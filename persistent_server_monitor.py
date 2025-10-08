#!/usr/bin/env python3
"""
Persistent Server Monitor
=========================

This script runs the agent server with persistent monitoring and logging
to capture why it might be stopping automatically.

Usage:
    python3 persistent_server_monitor.py agent_d --port 6002
"""

import os
import sys
import time
import signal
import subprocess
import threading
import traceback
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def log_with_timestamp(message):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    
    # Also write to log file
    with open("server_monitor.log", "a") as f:
        f.write(f"[{timestamp}] {message}\n")
        f.flush()

def check_system_resources():
    """Check system resources that might cause server to stop"""
    log_with_timestamp("🔍 Checking system resources...")
    
    try:
        # Check memory usage
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
            for line in meminfo.split('\n'):
                if 'MemAvailable' in line:
                    mem_available = line.split()[1]
                    log_with_timestamp(f"   Available memory: {mem_available} kB")
                    break
    except Exception as e:
        log_with_timestamp(f"   ⚠️ Could not check memory: {e}")
    
    try:
        # Check disk space
        import shutil
        total, used, free = shutil.disk_usage('/')
        log_with_timestamp(f"   Disk space: {free // (1024**3)} GB free of {total // (1024**3)} GB total")
    except Exception as e:
        log_with_timestamp(f"   ⚠️ Could not check disk space: {e}")
    
    try:
        # Check if port is in use
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', int(os.getenv('PORT', '6002'))))
        sock.close()
        if result == 0:
            log_with_timestamp(f"   ⚠️ Port {os.getenv('PORT', '6002')} is already in use!")
        else:
            log_with_timestamp(f"   ✅ Port {os.getenv('PORT', '6002')} is available")
    except Exception as e:
        log_with_timestamp(f"   ⚠️ Could not check port: {e}")

def monitor_process(process, agent_id):
    """Monitor the server process and log its behavior"""
    log_with_timestamp(f"🔍 Starting process monitor for {agent_id} (PID: {process.pid})")
    
    start_time = time.time()
    
    while True:
        try:
            # Check if process is still running
            poll_result = process.poll()
            
            if poll_result is not None:
                # Process has terminated
                end_time = time.time()
                runtime = end_time - start_time
                
                log_with_timestamp(f"❌ Server process terminated!")
                log_with_timestamp(f"   Exit code: {poll_result}")
                log_with_timestamp(f"   Runtime: {runtime:.2f} seconds")
                
                # Try to get any remaining output
                try:
                    stdout, stderr = process.communicate(timeout=5)
                    if stdout:
                        log_with_timestamp(f"   Final stdout: {stdout.decode()}")
                    if stderr:
                        log_with_timestamp(f"   Final stderr: {stderr.decode()}")
                except Exception as e:
                    log_with_timestamp(f"   Could not get final output: {e}")
                
                break
            
            # Process still running - log periodic status
            runtime = time.time() - start_time
            log_with_timestamp(f"✅ Server still running (PID: {process.pid}, Runtime: {runtime:.1f}s)")
            
            # Check system resources periodically
            if int(runtime) % 30 == 0:  # Every 30 seconds
                check_system_resources()
            
            time.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            log_with_timestamp(f"❌ Error in process monitor: {e}")
            traceback.print_exc()
            break

def run_server_with_monitoring(agent_id, port):
    """Run server with comprehensive monitoring"""
    log_with_timestamp(f"🚀 Starting monitored server for {agent_id} on port {port}")
    
    # Set environment variables
    os.environ['PORT'] = str(port)
    
    # Check initial system state
    check_system_resources()
    
    # Check if we can import required modules
    log_with_timestamp("🔍 Testing imports...")
    try:
        from nanda_adapter.simple import SimpleNANDA
        log_with_timestamp("   ✅ nanda_adapter.simple imported successfully")
    except Exception as e:
        log_with_timestamp(f"   ❌ Import error: {e}")
        return False
    
    try:
        from python_a2a import A2AServer, run_server
        log_with_timestamp("   ✅ python_a2a imported successfully")
    except Exception as e:
        log_with_timestamp(f"   ❌ Import error: {e}")
        return False
    
    # Try to create the agent first
    log_with_timestamp("🔍 Testing agent creation...")
    try:
        agent = SimpleNANDA(
            agent_id=agent_id,
            service_charge=10,
            require_anthropic=True
        )
        log_with_timestamp(f"   ✅ Agent {agent_id} created successfully")
        log_with_timestamp(f"   - Public URL: {agent.public_url}")
        log_with_timestamp(f"   - Internal bind: {agent.internal_host}:{agent.port}")
        log_with_timestamp(f"   - Service charge: {agent.service_charge} NP")
    except Exception as e:
        log_with_timestamp(f"   ❌ Agent creation failed: {e}")
        traceback.print_exc()
        with open("server_monitor.log", "a") as f:
            f.write(f"Agent creation traceback:\n")
            traceback.print_exc(file=f)
        return False
    
    # Start the server in a subprocess to monitor it
    log_with_timestamp("🚀 Starting server subprocess...")
    
    try:
        # Create command to run
        cmd = [
            sys.executable,  # Use same Python interpreter
            "interactive_agent_demo.py",
            agent_id,
            "--server-only",
            "--verbose",
            "--service-charge", "10"
        ]
        
        log_with_timestamp(f"   Command: {' '.join(cmd)}")
        
        # Start process with output capture
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        log_with_timestamp(f"   ✅ Process started with PID: {process.pid}")
        
        # Start output monitoring in separate threads
        def monitor_stdout():
            try:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        log_with_timestamp(f"STDOUT: {line.strip()}")
            except Exception as e:
                log_with_timestamp(f"Error reading stdout: {e}")
        
        def monitor_stderr():
            try:
                for line in iter(process.stderr.readline, ''):
                    if line:
                        log_with_timestamp(f"STDERR: {line.strip()}")
            except Exception as e:
                log_with_timestamp(f"Error reading stderr: {e}")
        
        stdout_thread = threading.Thread(target=monitor_stdout, daemon=True)
        stderr_thread = threading.Thread(target=monitor_stderr, daemon=True)
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Start process monitoring
        monitor_thread = threading.Thread(target=monitor_process, args=(process, agent_id), daemon=True)
        monitor_thread.start()
        
        # Wait for process to complete or be interrupted
        try:
            process.wait()
        except KeyboardInterrupt:
            log_with_timestamp("🛑 Received interrupt signal, stopping server...")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                log_with_timestamp("⚠️ Process didn't terminate gracefully, killing...")
                process.kill()
        
        return True
        
    except Exception as e:
        log_with_timestamp(f"❌ Failed to start subprocess: {e}")
        traceback.print_exc()
        with open("server_monitor.log", "a") as f:
            f.write(f"Subprocess start traceback:\n")
            traceback.print_exc(file=f)
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 persistent_server_monitor.py <agent_id> [--port <port>]")
        return 1
    
    agent_id = sys.argv[1]
    port = 6002  # Default port
    
    # Parse arguments
    if "--port" in sys.argv:
        try:
            port_idx = sys.argv.index("--port") + 1
            port = int(sys.argv[port_idx])
        except (ValueError, IndexError):
            print("Invalid port number")
            return 1
    
    # Initialize log file
    with open("server_monitor.log", "w") as f:
        f.write(f"=== Server Monitor Log Started ===\n")
    
    log_with_timestamp("🔍 Persistent Server Monitor Started")
    log_with_timestamp(f"   Agent ID: {agent_id}")
    log_with_timestamp(f"   Port: {port}")
    log_with_timestamp(f"   Python: {sys.version}")
    log_with_timestamp(f"   Working directory: {os.getcwd()}")
    log_with_timestamp(f"   Log file: server_monitor.log")
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        log_with_timestamp(f"🛑 Received signal {signum}, shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the server with monitoring
    success = run_server_with_monitoring(agent_id, port)
    
    if success:
        log_with_timestamp("✅ Server monitoring completed")
        return 0
    else:
        log_with_timestamp("❌ Server monitoring failed") 
        return 1

if __name__ == "__main__":
    sys.exit(main())