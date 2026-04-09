# 🔒 Deployment Safety Pattern - Never Get Locked Out Again

**Problem**: When hardening security (firewall rules, port restrictions), if your IP changes or Tailscale disconnects, you get locked out and must reset everything.

**Root Cause**: Security rules applied **before** testing access, no recovery path, no fallback mechanism.

**Solution**: **Layered Defense with Recovery Paths** (based on FORTRESS bulletproofing principles)

---

## The Pattern: "Safe Security Deployment"

### Phase 1: BEFORE Applying Security Rules

#### Step 1: Document Current State
```bash
# Save current firewall rules
sudo iptables-save > ~/firewall-backup-$(date +%Y%m%d-%H%M).rules

# Document current public IP
curl ifconfig.me > ~/my-ip-before-lockdown.txt

# Save Tailscale status
tailscale status > ~/tailscale-status.txt
```

#### Step 2: Create Recovery Script
**File**: `unlock-firewall.sh`
```bash
#!/bin/bash
# Emergency unlock script - runs on next boot
echo "🚨 EMERGENCY UNLOCK TRIGGERED"

# Reset iptables to defaults
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X

# Allow all traffic temporarily (DANGEROUS - remove after access restored)
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT

echo "✅ Firewall reset to permissive mode"
echo "⚠️  IMPORTANT: Re-apply security rules after regaining access"

# Remove this script after execution
rm /etc/init.d/unlock-firewall.sh
```

#### Step 3: Set Up Timed Fallback
```bash
# Create emergency unlock trigger
cat > /tmp/emergency-unlock.sh << 'EOF'
#!/bin/bash
# If this script runs, firewall is reset after 5 minutes
# Cancel with: rm /tmp/emergency-unlock.sh

echo "⏰ Emergency unlock scheduled in 5 minutes..."
echo "   Cancel with: rm /tmp/emergency-unlock.sh"

# Wait 5 minutes, then reset firewall
sleep 300

# Check if script still exists (wasn't cancelled)
if [ -f /tmp/emergency-unlock.sh ]; then
    echo "🔓 Executing emergency unlock..."
    iptables -F
    iptables -P INPUT ACCEPT
    echo "✅ Firewall reset - you should regain access"
fi
EOF

chmod +x /tmp/emergency-unlock.sh
```

---

### Phase 2: Apply Security Rules SAFELY

#### Rule 1: Always Keep SSH/Open Port Accessible
```bash
# ❌ WRONG: Lock yourself out immediately
iptables -A INPUT -s 192.168.1.100/32 -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -j DROP  # DANGEROous if IP changes!

# ✅ CORRECT: Keep fallback + add new rules
# 1. Keep existing SSH access (don't drop yet)
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 2. Add your IP restriction
iptables -A INPUT -s 192.168.1.100/32 -p tcp --dport 22 -j ACCEPT

# 3. Add Tailscale IP (if using)
iptables -A INPUT -s 100.x.x.x/32 -p tcp --dport 22 -j ACCEPT

# 4. TEST ACCESS BEFORE DROPPING!
# From another terminal/session, verify SSH still works
# Then and only then, add DROP rule
```

#### Rule 2: Use "Test and Confirm" Pattern
```bash
# Step 1: Add permissive rule first
iptables -A INPUT -p tcp --dport 8081 -j ACCEPT

# Step 2: Test from outside
curl http://your-server:8081/health

# Step 3: If works, add restrictive rule ABOVE permissive one
iptables -I INPUT 1 -s 192.168.1.100/32 -p tcp --dport 8081 -j ACCEPT

# Step 4: Test again
curl http://your-server:8081/health

# Step 5: If still works, remove permissive rule
iptables -D INPUT -p tcp --dport 8081 -j ACCEPT
```

#### Rule 3: Implement "Soft Lockout" with Timeout
```bash
# Instead of hard lockout, use timeout
iptables -A INPUT -p tcp --dport 22 -m recent --name ssh --set
iptables -A INPUT -p tcp --dport 22 -m recent --name ssh --rseconds 300 --hitcount 4 -j DROP

# This allows 4 SSH connections per 5 minutes, then temporary block
# Automatically recovers after timeout
```

---

### Phase 3: Recovery Mechanisms

#### Mechanism 1: Console Access (Oracle Cloud)
**For Oracle Cloud VMs**:
1. Go to Oracle Console → Compute → Instances
2. Click your instance
3. Click **"Console Connection"** (bottom of page)
4. Click **"Create Console Connection"**
5. Upload SSH key
6. Connect via serial console (bypasses firewall)

**This is your ultimate fallback** - always enable console access BEFORE locking down firewall.

#### Mechanism 2: Scheduled Reset
```bash
# Create a cron job that resets firewall daily at 4 AM
cat > /etc/cron.d/firewall-reset << 'EOF'
0 4 * * * root /usr/local/bin/reset-firewall-to-safe.sh
EOF

# reset-firewall-to-safe.sh:
#!/bin/bash
# Reset to known-good state
iptables-restore < /etc/iptables.rules.safe
```

#### Mechanism 3: Heartbeat Monitoring
```bash
# Install a watchdog that resets firewall if no heartbeat
cat > /usr/local/bin/firewall-watchdog.sh << 'EOF'
#!/bin/bash
# If no heartbeat file updated in 10 minutes, reset firewall
HEARTBEAT_FILE=/tmp/firewall-heartbeat
TIMEOUT=600  # 10 minutes

if [ -f "$HEARTBEAT_FILE" ]; then
    LAST_UPDATE=$(stat -c %Y "$HEARTBEAT_FILE")
    NOW=$(date +%s)
    AGE=$((NOW - LAST_UPDATE))
    
    if [ $AGE -gt $TIMEOUT ]; then
        echo "⚠️ Heartbeat timeout - resetting firewall"
        iptables -F
        iptables -P INPUT ACCEPT
    fi
fi
EOF

# Run every minute
* * * * * root /usr/local/bin/firewall-watchdog.sh
```

---

### Phase 4: Tailscale-Specific Protections

#### Problem: Tailscale IP Changes
When Tailscale reconnects, your tailnet IP might change, breaking firewall rules.

#### Solution 1: Use Tailscale Hostname, Not IP
```bash
# ❌ WRONG: Use static IP (changes)
iptables -A INPUT -s 100.123.45.67/32 -j ACCEPT

# ✅ CORRECT: Use hostname (updates automatically)
# Get current tailnet IP
TAILNET_IP=$(tailscale ip -4)

# Update firewall dynamically
iptables -D INPUT -s $OLD_TAILNET_IP/32 -j ACCEPT 2>/dev/null || true
iptables -A INPUT -s $TAILNET_IP/32 -j ACCEPT
echo "$TAILNET_IP" > /etc/tailscale-ip.txt

# Run this script when Tailscale reconnects
```

#### Solution 2: Tailscale Hook Script
```bash
# Create Tailscale up/down hooks
sudo mkdir -p /etc/tailscale/hooks

# Up hook (runs when Tailscale connects)
cat > /etc/tailscale/hooks/up.sh << 'EOF'
#!/bin/bash
# Update firewall with new Tailscale IP
TAILNET_IP=$(tailscale ip -4)
OLD_IP=$(cat /etc/tailscale-ip.txt 2>/dev/null || echo "")

# Remove old IP rule
if [ -n "$OLD_IP" ]; then
    iptables -D INPUT -s $OLD_IP/32 -j ACCEPT 2>/dev/null || true
fi

# Add new IP rule
iptables -A INPUT -s $TAILNET_IP/32 -p tcp --dport 22 -j ACCEPT
echo "$TAILNET_IP" > /etc/tailscale-ip.txt

echo "✅ Firewall updated for Tailscale IP: $TAILNET_IP"
EOF

chmod +x /etc/tailscale/hooks/up.sh

# Configure Tailscale to run hook
tailscale set --auto-update --login-server https://controlplane.tailscale.com
```

#### Solution 3: Keep Fallback Port Open
```bash
# Always keep port 22 open from ANY source during business hours
# This is your "break glass" emergency access
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Then add restrictive rules ABOVE it
iptables -I INPUT 1 -s 192.168.1.100/32 -p tcp --dport 22 -j ACCEPT

# If restrictive rule fails, the permissive rule below still works
# Not ideal security, but better than total lockout
```

---

### Phase 5: OneQueue-Specific Safety

#### For Your VPS (187.77.3.56)

**Current Risk**: If you lock port 22 or 8081, you lose access to OneQueue.

**Safe Deployment Pattern**:

```bash
# 1. BEFORE making firewall changes, ensure console access
# For Oracle Cloud: Enable "Console Connection"
# For other VPS: Have IPMI/iLO access or recovery mode

# 2. Create emergency unlock script
cat > /root/emergency-unlock.sh << 'EOF'
#!/bin/bash
echo "🚨 EMERGENCY UNLOCK TRIGGERED"
iptables -F
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT
echo "✅ All firewall rules removed"
echo "⚠️  Re-apply security rules immediately!"
EOF

chmod +x /root/emergency-unlock.sh

# 3. Set up automatic unlock after 10 minutes
# (gives you time to test before permanent lock)
(crontab -l 2>/dev/null; echo "*/10 * * * * /root/emergency-unlock.sh") | crontab -

# 4. Test your security changes
# - Apply rules
# - Test from outside
# - If works, make permanent
# - If fails, wait 10 minutes for auto-unlock

# 5. Once confident, remove auto-unlock
(crontab -l | grep -v "emergency-unlock.sh") | crontab -
```

#### For Docker Desktop Issues
**Problem**: Docker Desktop changes network config, breaks Tailscale, locks you out.

**Solution**:
```bash
# 1. Before installing Docker Desktop, save network state
sudo iptables-save > ~/pre-docker-iptables.rules

# 2. Install Docker Desktop in "safe mode" first
# Don't let it modify firewall yet

# 3. Test Tailscale still works

# 4. If breaks, restore immediately
sudo iptables-restore < ~/pre-docker-iptables.rules

# 5. Better: Use Docker Engine (not Desktop) on servers
sudo apt install docker.io docker-compose
```

---

## Quick Reference: Lockout Recovery

### If Already Locked Out:

1. **Oracle Cloud**: Use Console Connection (bypasses firewall)
2. **AWS EC2**: Use EC2 Instance Connect or Session Manager
3. **Azure**: Use Serial Console or Run Command
4. **GCP**: Use Cloud Shell or Serial Console

### If No Console Access:

1. **Reboot VM** (sometimes clears iptables if not persistent)
2. **Recovery Mode** (boot into single-user mode)
3. **Detach disk** (attach to another VM, edit files, reattach)

### Prevention (Always Do This First):

```bash
# 1. Enable console access BEFORE changes
# 2. Create emergency unlock script
# 3. Set up timed fallback (auto-unlock after 10 min)
# 4. Test from multiple locations
# 5. Have a colleague on standby to reboot if needed
```

---

## Checklist: Safe Security Deployment

### Before Applying Rules:
- [ ] Console access enabled and tested
- [ ] Emergency unlock script created
- [ ] Timed fallback configured (auto-unlock after 10 min)
- [ ] Current firewall rules backed up
- [ ] Tailscale status documented
- [ ] Public IP documented
- [ ] Colleague notified (backup person)

### During Rule Application:
- [ ] Add permissive rule first
- [ ] Test from outside
- [ ] Add restrictive rule above permissive
- [ ] Test again
- [ ] Remove permissive rule only after confirmation
- [ ] Keep emergency unlock script ready

### After Applying Rules:
- [ ] Test SSH access from multiple locations
- [ ] Test application access (port 8081, etc.)
- [ ] Test Tailscale connectivity
- [ ] Verify console access still works
- [ ] Remove timed fallback after 24 hours
- [ ] Document new firewall state
- [ ] Update runbooks with new access pattern

### Regular Maintenance:
- [ ] Review firewall rules monthly
- [ ] Test emergency unlock quarterly
- [ ] Update IP restrictions when IP changes
- [ ] Monitor logs for unauthorized access attempts
- [ ] Backup firewall rules after each change

---

## Key Principle: "Safe by Default, Secure by Choice"

**Don't**: Apply maximum security immediately and hope it works.

**Do**: Start permissive, test incrementally, then restrict.

**Worst case**: You're locked out and must reset everything.

**Best practice**: You have 5 different recovery paths and never truly lock yourself out.

---

**Remember**: The goal is **progressive security**, not **perfect security that locks you out**.

A slightly less secure system you can access is better than a "perfectly secure" system you can't recover.

---

*Created: 2026-04-09*  
*Based on: FORTRESS bulletproofing patterns + real lockout experience*  
*Status: CRITICAL - Read before ANY firewall changes*
