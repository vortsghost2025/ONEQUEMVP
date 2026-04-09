# Deploying API Key Rotation to VPS

## Quick Start (5 minutes)

### 1. Copy New Files to VPS

```bash
# From your local machine
scp app/services/nvidia_key_rotation.py root@187.77.3.56:/opt/onequeue/app/services/
scp app/services/nvidia_rotation.py root@187.77.3.56:/opt/onequeue/app/services/
scp app/services/example_nvidia_service.py root@187.77.3.56:/opt/onequeue/app/services/
scp docs/NVIDIA_KEY_ROTATION.md root@187.77.3.56:/opt/onequeue/docs/
```

### 2. Configure Multiple API Keys on VPS

Edit the `.env` file on VPS:

```bash
ssh root@187.77.3.56
cd /opt/onequeue
nano .env
```

Add your additional keys:

```bash
# Primary NVIDIA API Key
NVIDIA_API_KEY=nvapi-your-primary-key

# Additional keys for rotation
NVIDIA_API_KEY_1=nvapi-your-second-key
NVIDIA_API_KEY_2=nvapi-your-third-key
```

### 3. Rebuild Docker Container

```bash
cd /opt/onequeue
docker compose up -d --build onequeue
```

### 4. Verify Rotation is Working

Check logs for key initialization:

```bash
docker logs onequeue --tail 20 | grep -i "key"
```

You should see:
```
🔑 Initialized with 3 API key(s)
🔑 Added API key ending in ...abcd
🔑 Added API key ending in ...efgh
🔑 Added API key ending in ...ijkl
```

### 5. Test Rotation (Optional)

To test that rotation works, you can temporarily use a bad key as NVIDIA_API_KEY_1 and watch it rotate:

```bash
# Check current status
docker logs onequeue | grep "rotated\|Rate limit"
```

## Monitoring Rotation

### Check Key Status in Real-Time

```bash
# Watch for rotation events
docker logs -f onequeue | grep -E "rotated|Rate limit|cooldown"
```

### Expected Log Messages

**Normal Operation:**
```
🔑 Initialized with 3 API key(s)
✅ Request successful
```

**On Rate Limit (429):**
```
⚠️ Rate limit hit on key 1, rotating...
🔄 Rotated to API key 2/3
✅ Request successful with key 2
```

**Key Entering Cooldown:**
```
🔑 API key nvapi...abcd entered cooldown (3 failures)
```

## Troubleshooting

### Keys Not Rotating

1. Verify keys are configured correctly:
   ```bash
   docker exec onequeue env | grep NVIDIA
   ```

2. Check if keys are being loaded:
   ```bash
   docker logs onequeue | grep "Added API key"
   ```

### All Keys Failing

If all keys are failing:
1. Check each key individually (test outside OneQueue)
2. Verify keys haven't expired
3. Check NVIDIA dashboard for account issues
4. Reduce request rate if hitting limits frequently

### Want to Disable Rotation

Simply use only one key (remove NVIDIA_API_KEY_1, NVIDIA_API_KEY_2, etc.)

## Integration with Existing Code

To use key rotation in your existing NVIDIA service code:

### Option 1: Use the Decorator (Recommended)

```python
from app.services.nvidia_rotation import nvidia_api_retry_with_rotation

@nvidia_api_retry_with_rotation
def your_existing_function():
    # Your existing code here
    pass
```

### Option 2: Manual Key Management

```python
from app.services.nvidia_key_rotation import get_current_key, record_success, record_failure

try:
    key = get_current_key()
    # Make API call with key
    record_success()
except Exception as e:
    record_failure(getattr(e, 'status_code', None))
    raise
```

## Best Practices

1. **Use 3+ Keys**: Distribute load across multiple accounts
2. **Monitor Logs**: Watch for frequent rotation events
3. **Test Regularly**: Verify rotation works before you need it
4. **Document Keys**: Track which keys belong to which accounts
5. **Rotate Keys**: Periodically refresh API keys for security

## Rollback Plan

If you encounter issues:

1. Stop the container:
   ```bash
   docker compose stop onequeue
   ```

2. Revert to previous image:
   ```bash
   docker compose up -d --build onequeue  # Rebuilds with current code
   ```

3. Or restore from backup:
   ```bash
   # If you backed up before changes
   ```

## Next Steps

After deploying key rotation:
1. Monitor for 24 hours
2. Check rotation frequency
3. Adjust number of keys if needed
4. Consider adding metrics collection (Phase 2)

---

**Questions?** Check `docs/NVIDIA_KEY_ROTATION.md` for detailed guide.
