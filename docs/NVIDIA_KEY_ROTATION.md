# NVIDIA API Key Rotation - User Guide

## Overview

OneQueue now supports **automatic API key rotation** to handle rate limits gracefully. When you hit a 429 (rate limit) on one key, the system automatically rotates to the next available key.

## Features

- ✅ **Automatic 429 Detection**: System detects rate limit errors
- ✅ **Smart Key Rotation**: Switches to next key on rate limit
- ✅ **Exponential Backoff**: Each key has its own cooldown period
- ✅ **Circuit Breaker**: Temporarily disables failing keys
- ✅ **Health Tracking**: Monitors key usage and failure rates
- ✅ **Zero Downtime**: Seamless rotation without interrupting service

## Configuration

### Step 1: Add Multiple API Keys

Add your NVIDIA API keys to `.env` file:

```bash
# Primary key (required)
NVIDIA_API_KEY=nvapi-your-primary-key-here

# Additional keys for rotation (optional)
NVIDIA_API_KEY_1=nvapi-your-second-key-here
NVIDIA_API_KEY_2=nvapi-your-third-key-here
NVIDIA_API_KEY_3=nvapi-your-fourth-key-here
# Add as many as you need!
```

### Step 2: Use the Decorator

In your service class, use the `@nvidia_api_retry_with_rotation` decorator:

```python
from app.services.nvidia_rotation import nvidia_api_retry_with_rotation
from app.services.nvidia_key_rotation import get_current_key
import requests

class YourService:
    @nvidia_api_retry_with_rotation
    def call_nvidia(self, prompt: str):
        # Get current key (automatically rotates on 429)
        key = get_current_key()
        
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"prompt": prompt},
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
```

That's it! The decorator handles:
- Getting the current API key
- Detecting 429 errors
- Rotating to the next key
- Retrying with exponential backoff
- Tracking key health

## How It Works

### Rotation Logic

1. **Normal Operation**: Uses the first available healthy key
2. **On 429 Error**: 
   - Records failure for current key
   - Rotates to next available key
   - Retries the request
3. **On Key Cooldown**: 
   - Keys enter 5-minute cooldown after 3 failures
   - Automatically tries next key in rotation
4. **Recovery**: 
   - After cooldown period, key becomes available again
   - Success resets failure counter

### Key States

- **HEALTHY**: Key is available for use
- **COOLDOWN**: Key temporarily disabled (5 min after 3 failures)
- **EXHAUSTED**: Key permanently disabled (manual intervention needed)
- **INVALID**: Key format/auth error (permanent)

## Monitoring

Check the status of all your keys:

```python
from app.services.nvidia_key_rotation import get_rotator

rotator = get_rotator()
status = rotator.get_status()

print(f"Current key: {status['current_key']}/{status['total_keys']}")
print(f"Total rotations: {status['rotation_count']}")

for key_info in status['keys']:
    print(f"Key {key_info['id']}: {key_info['status']} "
          f"(failures: {key_info['failure_count']}, "
          f"requests: {key_info['total_requests']})")
```

## Example Output

```
🔑 Initialized with 3 API key(s)
🔑 Added API key ending in ...abcd
🔑 Added API key ending in ...efgh
🔑 Added API key ending in ...ijkl

⚠️ Rate limit hit on key 1, rotating...
🔄 Rotated to API key 2/3

✅ Request successful with key 2
```

## Best Practices

### 1. Use Multiple Keys from Different Accounts
- Distribute load across multiple NVIDIA developer accounts
- Each account gets separate rate limits
- Reduces impact of any single key hitting limits

### 2. Monitor Key Health
- Check logs for rotation events
- Set up alerts for frequent rotations
- Replace keys that frequently hit cooldown

### 3. Test Rotation
- Test with a known bad key to verify rotation works
- Monitor logs to confirm rotation behavior
- Verify fallback chain works end-to-end

### 4. Key Management
- Rotate keys periodically (security best practice)
- Keep backup keys in reserve
- Document which keys belong to which accounts

## Troubleshooting

### Problem: "No API keys configured"
**Solution**: Ensure at least `NVIDIA_API_KEY` is set in `.env`

### Problem: Keys not rotating
**Solution**: 
1. Check you have multiple keys configured (`NVIDIA_API_KEY_1`, `NVIDIA_API_KEY_2`, etc.)
2. Verify keys are valid format
3. Check logs for rotation events

### Problem: All keys in cooldown
**Solution**:
1. Wait for cooldown period (5 minutes) to expire
2. Add more API keys to increase capacity
3. Check if you're hitting rate limits too frequently (may need to reduce request rate)

### Problem: Frequent 429 errors
**Solution**:
1. Add more API keys to distribute load
2. Check if your usage pattern is causing bursts
3. Consider implementing request queuing/throttling
4. Contact NVIDIA about increasing rate limits

## Advanced Usage

### Manual Key Rotation

```python
from app.services.nvidia_key_rotation import get_rotator

rotator = get_rotator()

# Force rotation to next key
rotator.rotate()

# Reset all keys to healthy
rotator.reset_all()

# Get detailed status
status = rotator.get_status()
```

### Custom Error Handling

```python
from app.services.nvidia_key_rotation import record_failure, record_success

try:
    # Your API call here
    response = make_api_call()
    record_success()
except Exception as e:
    # Extract status code if available
    status_code = getattr(e, 'status_code', None)
    record_failure(status_code)
    raise
```

## Metrics to Track

- **Rotation Count**: How often keys are rotating (high = rate limit issues)
- **Failure Rate**: Percentage of failed requests per key
- **Cooldown Events**: How often keys enter cooldown
- **Key Utilization**: Distribution of requests across keys

## Security Notes

⚠️ **IMPORTANT**: 
- Never commit actual API keys to version control
- Use environment variables or secret management
- Rotate keys periodically
- Monitor for unusual usage patterns
- Use separate keys for development and production

## Support

For issues or questions:
1. Check logs for rotation events
2. Verify key configuration in `.env`
3. Test with a single key first
4. Review error messages for clues

---

**Example `.env` Configuration**:

```bash
# Production keys
NVIDIA_API_KEY=nvapi-prod-primary-key
NVIDIA_API_KEY_1=nvapi-prod-backup-key
NVIDIA_API_KEY_2=nvapi-prod-tertiary-key

# Development keys (separate from production)
# NVIDIA_API_KEY=nvapi-dev-key
```
