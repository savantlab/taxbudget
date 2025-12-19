# Rate Limiting

## Overview

The Tax Budget Allocator implements rate limiting to prevent abuse and ensure fair usage. Rate limiting protects the application from:
- Spam submissions
- Bot attacks
- Resource exhaustion
- Unfair manipulation of aggregate results

## Configuration

### Current Limits

**Allocation Submissions**: 10 per hour per user/IP
- Tracks by user cookie (if consented) or IP address
- Resets every hour
- Returns user-friendly error message when exceeded

### Implementation

Rate limiting is implemented using `django-ratelimit` with Redis as the backend.

**File**: `allocator/views.py`

```python
@ratelimit(key=ratelimit_key, rate='10/h', method='POST', block=False)
def allocate_view(request):
    # Check if rate limited
    if request.method == 'POST' and getattr(request, 'limited', False):
        messages.error(request, 'Rate limit exceeded. You can submit up to 10 allocations per hour.')
        # Return form with error
```

**Rate Limit Key Function**:
```python
def ratelimit_key(group, request):
    """Rate limit key: prefer user cookie, fallback to IP"""
    user_id = request.COOKIES.get('tax_allocator_user_id')
    if user_id:
        return f'user:{user_id}'
    return f'ip:{get_client_ip(request)}'
```

## How It Works

### 1. Tracking Method
- **With Cookie Consent**: Tracks by user UUID (stored in `tax_allocator_user_id` cookie)
- **Without Cookie Consent**: Tracks by IP address (from `X-Forwarded-For` header or `REMOTE_ADDR`)

### 2. Behind CDN/Proxy
The app correctly extracts the real client IP even when behind DigitalOcean App Platform's CDN:

```python
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]  # First IP is the client
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
```

### 3. Storage
Rate limit counters are stored in Redis with automatic expiration:
- Key format: `rl:allocate_view:user:<user_id>` or `rl:allocate_view:ip:<ip_address>`
- Expiration: 1 hour (3600 seconds)
- Automatic cleanup: Redis handles TTL

### 4. User Experience
When rate limited, users see:
- Error message: "Rate limit exceeded. You can submit up to 10 allocations per hour. Please try again later."
- Form remains populated with their data
- No redirect (stays on same page)

## Testing

### Manual Testing

1. **Start Django server**:
   ```bash
   python manage.py runserver
   ```

2. **Run test script**:
   ```bash
   python test_rate_limiting.py
   ```

Expected output:
```
Request 1: ✅ Success
Request 2: ✅ Success
...
Request 10: ✅ Success
Request 11: ❌ RATE LIMITED

✅ Rate limiting is working correctly!
```

### Testing Without Cookie
To test IP-based rate limiting:
1. Clear cookies or use incognito mode
2. Submit form 11 times
3. 11th submission should be blocked

### Testing With Cookie
To test user-based rate limiting:
1. Accept cookie consent
2. Submit form 10 times (cookie tracks you)
3. Open new incognito window → you can submit 10 more (different user)
4. Original window → still blocked (same user)

## Monitoring

### Check Rate Limit Status (Redis)

```bash
# Connect to Redis
redis-cli

# View all rate limit keys
KEYS rl:*

# Check specific user's limit
GET rl:allocate_view:user:<user_id>

# Check TTL (time until reset)
TTL rl:allocate_view:user:<user_id>

# View all rate limit counters
SCAN 0 MATCH rl:* COUNT 100
```

### Clear Rate Limits (Emergency)

```bash
# Clear all rate limits
redis-cli KEYS "rl:*" | xargs redis-cli DEL

# Clear specific user
redis-cli DEL rl:allocate_view:user:<user_id>

# Clear specific IP
redis-cli DEL rl:allocate_view:ip:<ip_address>
```

## Customization

### Change Rate Limit

Edit `allocator/views.py`:

```python
# Current: 10 per hour
@ratelimit(key=ratelimit_key, rate='10/h', method='POST', block=False)

# Examples of other rates:
@ratelimit(key=ratelimit_key, rate='5/h', ...)   # 5 per hour (stricter)
@ratelimit(key=ratelimit_key, rate='100/d', ...) # 100 per day
@ratelimit(key=ratelimit_key, rate='1/m', ...)   # 1 per minute
@ratelimit(key=ratelimit_key, rate='50/h', ...)  # 50 per hour (more lenient)
```

### Change Tracking Method

**Track only by IP** (ignore cookies):
```python
@ratelimit(key='ip', rate='10/h', method='POST', block=False)
```

**Track only by user cookie** (no IP fallback):
```python
def user_only(group, request):
    return request.COOKIES.get('tax_allocator_user_id', 'anonymous')

@ratelimit(key=user_only, rate='10/h', method='POST', block=False)
```

**Track by header** (e.g., API key):
```python
@ratelimit(key='header:x-api-key', rate='1000/h', method='POST', block=False)
```

### Block vs Warn

**Current behavior** (`block=False`): Shows error message, returns form
**Blocking behavior** (`block=True`): Returns HTTP 429 (Too Many Requests)

```python
@ratelimit(key=ratelimit_key, rate='10/h', method='POST', block=True)
```

## Production Considerations

### 1. Redis Availability
- Rate limiting requires Redis
- If Redis is down, rate limiting fails open (allows all requests)
- Monitor Redis uptime

### 2. Distributed Redis
For multi-server deployments, use a shared Redis instance:
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.client.DefaultClient',
        'LOCATION': 'redis://redis-primary:6379/0',  # Shared Redis
    }
}
```

### 3. False Positives
Behind NAT/corporate networks, multiple users may share one IP:
- Consider increasing limit for GET requests
- Keep POST submissions strict (10/hour is reasonable)

### 4. DDoS Protection
Rate limiting helps but isn't sufficient for large-scale DDoS:
- Use DigitalOcean's built-in DDoS protection
- Consider Cloudflare if under sustained attack
- Implement WAF rules for known attack patterns

## Troubleshooting

### Issue: All users getting rate limited
**Cause**: App not extracting real IP (sees all requests from CDN IP)
**Solution**: Verify `X-Forwarded-For` header is being read correctly

```python
# Test in Django shell
python manage.py shell
>>> from django.test import RequestFactory
>>> request = RequestFactory().post('/')
>>> request.META['HTTP_X_FORWARDED_FOR'] = '1.2.3.4, 5.6.7.8'
>>> from allocator.views import get_client_ip
>>> get_client_ip(request)
'1.2.3.4'  # Should return first IP
```

### Issue: Rate limiting not working
**Cause**: Redis not running or not connected
**Solution**: 
```bash
# Check Redis
redis-cli ping  # Should return PONG

# Check Django cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('test', 'value')
>>> cache.get('test')
'value'
```

### Issue: Rate limits not resetting
**Cause**: TTL not set correctly
**Solution**: Check Redis keys have TTL
```bash
redis-cli TTL rl:allocate_view:ip:127.0.0.1
# Should return number of seconds until expiration (not -1)
```

## Security Notes

1. **IP Spoofing**: Trust `X-Forwarded-For` only when behind trusted proxy (DigitalOcean App Platform)
2. **Cookie Manipulation**: Users can delete cookies to reset limit (acceptable for this use case)
3. **Bypass Prevention**: Cannot fully prevent determined attackers, but raises the bar significantly
4. **Privacy**: IP addresses are hashed in Redis keys, not stored in plaintext

## Future Enhancements

- [ ] Admin dashboard to view rate limit violations
- [ ] Email alerts for suspected abuse (e.g., 50+ failed attempts)
- [ ] Progressive rate limiting (stricter after first violation)
- [ ] Whitelist for trusted IPs/users
- [ ] Captcha after rate limit exceeded
- [ ] Temporary bans for repeated violations

## References

- [django-ratelimit Documentation](https://django-ratelimit.readthedocs.io/)
- [Redis TTL Documentation](https://redis.io/commands/ttl)
- [HTTP 429 Status Code](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429)
