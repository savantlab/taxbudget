# Cookie-Based User Tracking

## Overview

The Tax Budget Allocator now uses cookies to track users across multiple submissions, allowing them to view their submission history while maintaining anonymity.

## Features

### 🍪 Cookie-Based Tracking
- **Cookie Name**: `tax_allocator_user_id`
- **Value**: UUID v4 (e.g., `550e8400-e29b-41d4-a716-446655440000`)
- **Expiration**: 1 year
- **Security**: HttpOnly, SameSite=Lax
- **Storage**: Client-side only (not stored in session)

### 📊 Submission History
- Users can view all their previous submissions at `/history/`
- Shows submission date, allocations, and session keys
- Accessible via "My History" in navigation menu

### 👤 Returning User Detection
- Welcome message on homepage for returning users
- Shows count of previous submissions
- Quick link to view full history

## How It Works

### First Visit
1. User submits allocation form
2. System generates new `user_id` (UUID)
3. Cookie is set in response with 1-year expiration
4. Submission is saved with `user_id` in database

### Returning Visits
1. Cookie is read from request
2. User sees welcome message with submission count
3. Previous submissions are linked to this `user_id`
4. New submissions continue to use same `user_id`

## Database Schema

### UserAllocation Model
```python
session_key = models.CharField(max_length=255, db_index=True)  # Per-submission ID
user_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)  # Cross-submission ID
category = models.ForeignKey(BudgetCategory, on_delete=models.CASCADE)
percentage = models.DecimalField(max_digits=5, decimal_places=2)
created_at = models.DateTimeField(default=timezone.now, db_index=True)
ip_address = models.GenericIPAddressField(null=True, blank=True)
```

### AllocationSubmission Model
```python
session_key = models.CharField(max_length=255, db_index=True)  # Per-submission ID
user_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)  # Cross-submission ID
submitted_at = models.DateTimeField(default=timezone.now, db_index=True)
ip_address = models.GenericIPAddressField(null=True, blank=True)
```

## New URLs

| URL | Name | Description |
|-----|------|-------------|
| `/history/` | `history` | View user's submission history |

## Privacy & Security

### ✅ Privacy Features
- **Anonymous**: No personal information collected
- **Client-side**: Cookie stored only on user's device
- **No tracking pixels**: No third-party tracking
- **No fingerprinting**: No device/browser fingerprinting
- **Optional**: Users can clear cookies to reset tracking

### 🔒 Security Features
- **HttpOnly**: Cookie cannot be accessed via JavaScript
- **SameSite=Lax**: Protection against CSRF attacks
- **No sensitive data**: Cookie only contains UUID
- **Indexed queries**: Fast database lookups

## User Experience

### Navigation
```
[New Allocation] [My History] [Aggregate Results]
```

### Homepage (Returning User)
```
👤 Welcome back! You have 3 previous submissions. [View History]
```

### History Page
- Cards displaying each submission
- Date/time of submission
- All category allocations
- Link to detailed results view

## Cookie Lifecycle

```
┌─────────────────────┐
│  First Submission   │
│                     │
│  1. Generate UUID   │
│  2. Save to DB      │
│  3. Set Cookie      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Returning Visit    │
│                     │
│  1. Read Cookie     │
│  2. Load History    │
│  3. Show Welcome    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  New Submission     │
│                     │
│  1. Use Existing ID │
│  2. Save to DB      │
│  3. Update Cookie   │
└─────────────────────┘
```

## Managing Cookies

### View Your User ID (Browser Console)
```javascript
document.cookie.split('; ').find(row => row.startsWith('tax_allocator_user_id'))
```

### Clear Your History
**Option 1: Clear Specific Cookie**
- Browser Settings → Privacy → Cookies → Delete `tax_allocator_user_id`

**Option 2: Clear All Cookies**
- Browser Settings → Privacy → Clear Browsing Data → Cookies

**Note**: This only removes the cookie from your device. Your submissions remain in the database but won't be linked to you anymore.

## Technical Implementation

### Setting Cookie (views.py)
```python
def get_or_create_user_id(request):
    """Get user_id from cookie or generate a new one"""
    user_id = request.COOKIES.get('tax_allocator_user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
    return user_id

# In allocate_view
user_id = get_or_create_user_id(request)
response.set_cookie(
    'tax_allocator_user_id',
    user_id,
    max_age=365*24*60*60,  # 1 year
    httponly=True,
    samesite='Lax'
)
```

### Reading Cookie (views.py)
```python
# Check for previous submissions
user_id = request.COOKIES.get('tax_allocator_user_id')
if user_id:
    previous_submissions = AllocationSubmission.objects.filter(
        user_id=user_id
    ).order_by('-submitted_at')[:5]
```

## Analytics Possibilities

With user_id tracking, you can now analyze:
- **Submission frequency**: How often users return
- **Allocation changes**: How opinions evolve over time
- **Retention**: User engagement metrics
- **Patterns**: Common allocation strategies

### Example Queries

**Count returning users:**
```python
AllocationSubmission.objects.values('user_id').annotate(
    count=Count('id')
).filter(count__gt=1).count()
```

**Average submissions per user:**
```python
AllocationSubmission.objects.values('user_id').annotate(
    count=Count('id')
).aggregate(Avg('count'))
```

**User allocation trends:**
```python
UserAllocation.objects.filter(
    user_id='<uuid>'
).order_by('created_at').values('category__name', 'percentage', 'created_at')
```

## Migration

The feature was added via migration `0002_allocationsubmission_user_id_userallocation_user_id_and_more.py`:
- Added `user_id` field to both models (nullable for backward compatibility)
- Added database indexes for efficient queries
- Existing submissions remain accessible via `session_key`

## Backward Compatibility

✅ **Fully backward compatible**
- Existing submissions work without user_id
- Old session-based flows still function
- user_id is optional (null=True, blank=True)
- No breaking changes to existing features

## Future Enhancements

Possible additions:
1. **Export history**: Download CSV of all submissions
2. **Compare submissions**: Side-by-side comparison tool
3. **Trends chart**: Visualize allocation changes over time
4. **Email notifications**: Optional email updates (requires auth)
5. **Shared profiles**: Public/shareable allocation profiles
6. **Delete history**: User-initiated data deletion

## Testing

### Manual Testing
1. Submit allocation (first time)
2. Check cookie in browser DevTools
3. Submit another allocation
4. Visit `/history/` to see both submissions
5. Clear cookies
6. Submit new allocation (new user_id created)

### Automated Testing
```python
# Test cookie creation
response = client.post('/submit/', data={...})
assert 'tax_allocator_user_id' in response.cookies

# Test history view
client.cookies['tax_allocator_user_id'] = 'test-uuid'
response = client.get('/history/')
assert response.status_code == 200
```

## Compliance

### GDPR Considerations
- ✅ No personal data collected
- ✅ Anonymous identifiers only
- ✅ User can delete cookie anytime
- ⚠️ Consider adding cookie consent banner
- ⚠️ Provide data deletion endpoint

### Cookie Consent
Consider adding a banner:
```
"🍪 We use cookies to remember your submissions. No personal data is collected."
[Accept] [Learn More]
```

## Summary

**Added:**
- Cookie-based user tracking
- Submission history page
- Welcome message for returning users
- Navigation link to history

**Database Changes:**
- Added `user_id` field to `UserAllocation`
- Added `user_id` field to `AllocationSubmission`
- Added indexes for performance

**Files Modified:**
- `allocator/models.py` - Added user_id fields
- `allocator/views.py` - Cookie handling and history view
- `allocator/urls.py` - History URL pattern
- `allocator/templates/allocator/base.html` - Navigation link
- `allocator/templates/allocator/allocate.html` - Welcome message
- `allocator/templates/allocator/history.html` - New template

**Migration:**
- `0002_allocationsubmission_user_id_userallocation_user_id_and_more.py`
