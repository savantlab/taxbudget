# DNS Setup Guide
## Configure tadpollster.com with Squarespace DNS

**Domain**: tadpollster.com  
**Registrar**: Squarespace  
**Target**: DigitalOcean App Platform

---

## Overview

You're keeping your domain registered with Squarespace and just pointing it to DigitalOcean. No need to transfer the domain or change nameservers.

---

## Prerequisites

✅ Domain registered at Squarespace: tadpollster.com  
✅ DigitalOcean account authenticated: doctl  
✅ App ready to deploy: Tax Budget Allocator

---

## Step-by-Step Setup

### Step 1: Deploy Your App (Do This First!)

```bash
cd /Users/savantlab/Savantlab/taxbudget

# Commit and push to GitHub
git add .
git commit -m "Initial commit: Tax Budget Allocator"
git push -u origin main

# Deploy to DigitalOcean
doctl apps create --spec do-app-spec.yaml
```

**Save the output!** You'll see something like:
```
Notice: App created
ID: abc123def-456g-789h-0ijk-123456789abc
Default Ingress: your-app-randomstring.ondigitalocean.app
```

**Your DigitalOcean URL**: `your-app-randomstring.ondigitalocean.app`

### Step 2: Configure DNS at Squarespace

1. **Log in to Squarespace**
   - Go to https://account.squarespace.com

2. **Navigate to DNS Settings**
   - Click on your domain: **tadpollster.com**
   - Go to **DNS Settings** or **Advanced DNS**

3. **Add CNAME Record for Root Domain**
   ```
   Type:      CNAME (or ALIAS if available)
   Name:      @ (or leave blank, or "tadpollster.com")
   Content:   your-app-randomstring.ondigitalocean.app
   TTL:       3600 (or Auto)
   ```

4. **Add CNAME Record for www Subdomain**
   ```
   Type:      CNAME
   Name:      www
   Content:   your-app-randomstring.ondigitalocean.app
   TTL:       3600 (or Auto)
   ```

5. **Save Changes**

### Step 3: Alternative (If CNAME @ Not Allowed)

Some registrars (including some Squarespace plans) don't allow CNAME for root domain.

**Option A: Use A Record Instead**

First, get your app's IP address:
```bash
# Get app ID
APP_ID=$(doctl apps list --format ID --no-header)

# Get app info
doctl apps get $APP_ID

# Look for the IP address in the output
```

Then add:
```
Type:      A
Name:      @ (or leave blank)
Content:   <your-app-ip-address>
TTL:       3600
```

**Option B: Use Domain Forwarding**

If Squarespace doesn't allow either:
1. Set up **Domain Forwarding** from `tadpollster.com` → `www.tadpollster.com`
2. Only configure CNAME for `www`

### Step 4: Verify DNS Configuration

Wait 5-30 minutes for DNS propagation, then check:

```bash
# Check root domain
dig tadpollster.com

# Check www subdomain
dig www.tadpollster.com

# Should show CNAME pointing to your-app-randomstring.ondigitalocean.app
```

**Online checker:**
- https://dnschecker.org
- Enter: tadpollster.com
- Type: CNAME

### Step 5: Configure Domain in DigitalOcean

The domain should already be configured via `do-app-spec.yaml`, but verify:

1. **Via Dashboard:**
   - Go to https://cloud.digitalocean.com/apps
   - Click your app
   - Go to **Settings** → **Domains**
   - Should see: `tadpollster.com` (Primary)
   - Should see: `www.tadpollster.com` (Alias)

2. **Via CLI:**
   ```bash
   doctl apps get $APP_ID
   # Look for "domains" section
   ```

If not configured, add manually:
```bash
# Via dashboard: Settings → Domains → Add Domain
# Enter: tadpollster.com
```

### Step 6: Wait for SSL Certificate

DigitalOcean automatically provisions Let's Encrypt SSL certificates.

**Timeline:**
1. DNS propagation: 5-30 minutes
2. SSL provisioning: 5-10 minutes after DNS resolves
3. Total: Usually 15-45 minutes

**Check SSL status:**
```bash
# Try accessing your site
curl -I https://tadpollster.com

# Should return: HTTP/2 200
```

**Or in browser:**
- https://tadpollster.com
- Look for 🔒 padlock icon

---

## DNS Record Summary

After setup, your DNS should look like:

| Type  | Host | Points To | TTL |
|-------|------|-----------|-----|
| CNAME | @    | your-app-randomstring.ondigitalocean.app | 3600 |
| CNAME | www  | your-app-randomstring.ondigitalocean.app | 3600 |

**Or (if CNAME @ not allowed):**

| Type  | Host | Points To | TTL |
|-------|------|-----------|-----|
| A     | @    | 123.45.67.89 | 3600 |
| CNAME | www  | your-app-randomstring.ondigitalocean.app | 3600 |

---

## Troubleshooting

### DNS Not Resolving

**Check DNS propagation:**
```bash
dig tadpollster.com
nslookup tadpollster.com
```

**Common issues:**
- **Too early**: Wait 30 minutes minimum
- **Wrong record**: Verify you added CNAME, not A (unless intentional)
- **Wrong value**: Must be `your-app.ondigitalocean.app`, not `http://` or `https://`
- **Typo**: Double-check the DigitalOcean app URL

### SSL Certificate Not Issued

**Check DNS first:**
```bash
dig tadpollster.com
# Must resolve to DigitalOcean before SSL can be issued
```

**Common issues:**
- DNS not propagated yet (wait longer)
- DNS pointing to wrong location
- Domain not added to DigitalOcean app

**Force SSL retry:**
1. Go to DigitalOcean dashboard
2. Apps → Your App → Settings → Domains
3. Click "Refresh" or remove/re-add domain

### Site Not Loading

**Check app status:**
```bash
doctl apps get $APP_ID
```

**Check app logs:**
```bash
doctl apps logs $APP_ID --type run --follow
```

**Verify SECRET_KEY is set:**
1. Dashboard → Apps → Your App → Settings → Environment Variables
2. Check SECRET_KEY is configured for all services

### Wrong App URL

**Get correct app URL:**
```bash
APP_ID=$(doctl apps list --format ID --no-header)
doctl apps get $APP_ID --format DefaultIngress --no-header
```

---

## Squarespace-Specific Notes

### DNS Settings Location

Squarespace DNS settings are usually at:
- **Settings** → **Domains** → **Your Domain** → **DNS Settings**

Or directly:
- https://account.squarespace.com/domains/managed/{your-domain}/dns

### CNAME Flattening

Squarespace supports **CNAME flattening** which allows CNAME at root:
- This means you CAN use CNAME for `@` record
- No need for A record workaround

### TTL Settings

Squarespace may use "Auto" TTL:
- This is fine, usually defaults to 3600 seconds
- Lower TTL (300-600) allows faster changes but slightly slower DNS

### Domain Forwarding

If needed, set up forwarding:
1. **Settings** → **Domains** → **Your Domain**
2. Click **Advanced Settings**
3. Enable **Domain Forwarding**
4. Forward: `tadpollster.com` → `www.tadpollster.com`
5. Enable **301 Permanent Redirect**

---

## Testing Your Setup

### Complete Test Checklist

```bash
# 1. Check DNS resolution
dig tadpollster.com
dig www.tadpollster.com

# 2. Test HTTP redirect (should redirect to HTTPS)
curl -I http://tadpollster.com

# 3. Test HTTPS
curl -I https://tadpollster.com
curl -I https://www.tadpollster.com

# 4. Test in browser
open https://tadpollster.com
```

**Expected results:**
- ✅ DNS resolves to DigitalOcean
- ✅ HTTP redirects to HTTPS
- ✅ HTTPS loads with valid certificate
- ✅ Both `tadpollster.com` and `www.tadpollster.com` work
- ✅ Application loads correctly

---

## Quick Reference Commands

```bash
# Get app info
doctl apps list
doctl apps get <app-id>

# Check DNS
dig tadpollster.com
dig www.tadpollster.com

# Test site
curl -I https://tadpollster.com

# View logs
doctl apps logs <app-id> --type run --follow

# Check SSL status
curl -vI https://tadpollster.com 2>&1 | grep -i ssl
```

---

## Timeline

| Step | Duration | Total Time |
|------|----------|------------|
| Deploy app | 5-10 min | 10 min |
| Configure DNS | 2 min | 12 min |
| DNS propagation | 5-30 min | 15-45 min |
| SSL provisioning | 5-10 min | 20-55 min |
| **Total** | **Variable** | **20-55 min** |

---

## What You're NOT Doing

❌ **NOT** transferring domain from Squarespace  
❌ **NOT** changing nameservers  
❌ **NOT** adding Squarespace to DigitalOcean  
❌ **NOT** manually configuring SSL  
❌ **NOT** managing IP addresses (unless using A records)

## What You ARE Doing

✅ Deploying app to DigitalOcean  
✅ Getting DigitalOcean app URL  
✅ Adding CNAME records at Squarespace  
✅ Pointing domain to DigitalOcean  
✅ Waiting for DNS + SSL (automatic)

---

## Summary

Your setup is:

```
tadpollster.com (Squarespace DNS)
         ↓ CNAME
your-app.ondigitalocean.app (DigitalOcean App Platform)
         ↓
Tax Budget Allocator (Django App)
```

**Squarespace**: Domain registrar + DNS hosting  
**DigitalOcean**: Application hosting  
**DNS Records**: Bridge between the two

Simple! 🚀

---

## Need Help?

**Documentation:**
- `DEPLOYMENT_QUICKSTART.md` - Full deployment guide
- `DIGITALOCEAN_DEPLOYMENT.md` - Complete reference
- `DEPLOY_NOW.md` - Quick 4-step guide

**Check Status:**
```bash
# App status
doctl apps list

# DNS status
dig tadpollster.com

# Site status
curl -I https://tadpollster.com
```

**Squarespace Support:**
- https://support.squarespace.com/hc/en-us/articles/205812378-Connecting-a-domain-to-your-site

**DigitalOcean Support:**
- https://docs.digitalocean.com/products/app-platform/how-to/manage-domains/
