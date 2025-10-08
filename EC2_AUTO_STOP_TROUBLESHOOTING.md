# EC2 Agent Auto-Stop Troubleshooting Guide

## 🔍 Problem: Agent Server Automatically Stopping

If your `agent_d` server is automatically stopping on EC2, here are the most common causes and solutions:

## 🚀 Quick Fix Steps

### 1. Use the Persistent Server Starter (Recommended)
```bash
# On your EC2 instance
cd adapter
./start_persistent_agent.sh agent_d 6002 10
```

This will:
- Start the agent in a `screen` session that persists after SSH disconnection
- Set proper environment variables
- Allow you to reconnect to see logs

### 2. Run Diagnostic Tool
```bash
# Check for common issues that cause auto-stopping
python3 diagnose_auto_stop.py agent_d 6002
```

### 3. Use the Crash Monitor
```bash
# Monitor exactly why the server stops
./simple_crash_monitor.sh agent_d 6002
```

## 🔧 Common Causes & Solutions

### 1. SSH Disconnection Kills Process
**Problem**: Server stops when you disconnect from SSH
**Solution**: Use screen/tmux or nohup

```bash
# Using screen (recommended)
screen -S agent_d
cd adapter && source venv/bin/activate
python3 interactive_agent_demo.py agent_d --server-only --verbose
# Press Ctrl+A then D to detach
# Reconnect with: screen -r agent_d

# Using nohup
nohup python3 interactive_agent_demo.py agent_d --server-only --verbose > agent_d.log 2>&1 &
```

### 2. Port Already in Use
**Problem**: Another process is using port 6002
**Check**: 
```bash
netstat -tulpn | grep :6002
lsof -i :6002
```
**Solution**: Kill the conflicting process or use a different port

### 3. Memory/Resource Limits
**Problem**: EC2 instance runs out of memory
**Check**:
```bash
free -h
df -h
```
**Solution**: Use a larger EC2 instance or optimize memory usage

### 4. Missing Dependencies
**Problem**: Required Python packages not installed
**Check**:
```bash
cd adapter
source venv/bin/activate
python3 -c "import anthropic, python_a2a, flask"
```
**Solution**: Reinstall dependencies
```bash
pip install -r requirements.txt
```

### 5. Environment Variables Missing
**Problem**: ANTHROPIC_API_KEY or other required vars not set
**Check**:
```bash
echo $ANTHROPIC_API_KEY
cat .env
```
**Solution**: Set environment variables in `.env` file

### 6. Python Process Crashes
**Problem**: Unhandled exception causes process to exit
**Check**: Look at logs with verbose output
```bash
python3 interactive_agent_demo.py agent_d --server-only --verbose --debug
```

## 📊 Debugging Commands

### Check if agent is running
```bash
# Check process
ps aux | grep interactive_agent_demo
ps aux | grep python

# Check port
netstat -tulpn | grep :6002
curl http://localhost:6002/health
```

### Monitor logs in real-time
```bash
# If using screen
screen -r agent_d

# If using nohup
tail -f agent_d.log

# If using systemd log
journalctl -f -u your-service-name
```

### Check system resources
```bash
# Memory usage
free -h
top

# Disk usage
df -h

# System logs
tail -f /var/log/syslog
dmesg | tail
```

## 🛠️ Advanced Debugging

### 1. Use the Persistent Monitor
```bash
python3 persistent_server_monitor.py agent_d --port 6002
```

This will:
- Monitor the process continuously
- Log detailed startup information
- Capture exact exit codes and error messages
- Monitor system resources

### 2. Enable Debug Logging
```bash
python3 interactive_agent_demo.py agent_d --server-only --verbose --debug
```

### 3. Check Python Path and Imports
```bash
python3 -c "
import sys
print('Python path:', sys.path)
try:
    from nanda_adapter.simple import SimpleNANDA
    print('✅ nanda_adapter import ok')
except Exception as e:
    print('❌ nanda_adapter import failed:', e)
"
```

## 🎯 Step-by-Step Troubleshooting

1. **Connect to your EC2 instance**
   ```bash
   ssh -i nanda-agent-key.pem ubuntu@52.20.124.144
   ```

2. **Navigate to project directory**
   ```bash
   cd adapter
   ```

3. **Run the diagnostic tool**
   ```bash
   python3 diagnose_auto_stop.py agent_d 6002
   ```

4. **Fix any issues found by the diagnostic**

5. **Start with the persistent starter**
   ```bash
   ./start_persistent_agent.sh agent_d 6002 10
   ```

6. **If still failing, use the crash monitor**
   ```bash
   ./simple_crash_monitor.sh agent_d 6002
   ```

7. **Check the detailed logs**
   ```bash
   cat crash_monitor_agent_d.log
   ```

## 📋 Expected Successful Output

When working correctly, you should see:
```
🚀 Agent 'agent_d' starting
🔗 Public URL: http://52.20.124.144:6002
🌐 Internal bind: 0.0.0.0:6002
📝 Logs: logs/agent_agent_d

Press Ctrl+C to stop

Starting A2A server on http://0.0.0.0:6002/a2a
Google A2A compatibility: Enabled
 * Serving Flask app 'python_a2a.server.http'
 * Running on all addresses (0.0.0.0)
 * Running on http://52.20.124.144:6002
```

The server should then continue running and responding to requests.

## 💡 Prevention Tips

1. **Always use screen or tmux** for long-running processes
2. **Monitor system resources** before starting
3. **Use verbose logging** during initial deployment
4. **Test locally first** with same configuration
5. **Keep logs** for troubleshooting

Run the diagnostic tool and let me know what issues it finds!