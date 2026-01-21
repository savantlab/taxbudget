# Social Media Preview Image

## What Was Added

Added comprehensive social media meta tags to `base.html`:
- **Open Graph** tags (Facebook, LinkedIn, etc.)
- **Twitter Card** tags (large image card)
- **Primary meta tags** (title, description, keywords)
- **Theme color** for mobile browsers

## Preview Image Needed

The meta tags reference: `https://tadpollster.com/static/social-preview.png`

### Recommended Specifications
- **Size:** 1200×630 pixels (Twitter/Facebook optimal)
- **Format:** PNG or JPG
- **File size:** < 1MB
- **Content:** Your brand + clear value proposition

### Quick Options

#### Option 1: Use Canva (Easiest)
1. Go to canva.com
2. Select "Twitter Post" template (1200×630)
3. Use your brand colors: #10b981 (green)
4. Add text:
   - Title: "Tax Budget Allocator"
   - Subtitle: "Where Would You Spend Your Tax Dollars?"
   - Emoji: 💰 or 🏛️
5. Download as PNG
6. Save to: `taxbudget/allocator/static/social-preview.png`

#### Option 2: Use Screenshot
1. Take a high-res screenshot of tadpollster.com
2. Crop to 1200×630
3. Add border or overlay with title text

#### Option 3: HTML Canvas (Generate Programmatically)
See `generate_social_preview.html` below for a template

## Testing Social Cards

### Twitter/X
Paste your URL here: https://cards-dev.twitter.com/validator

### Facebook
Paste your URL here: https://developers.facebook.com/tools/debug/

### LinkedIn
Share your URL in a post to see preview

## Example Social Preview HTML Generator

Save this as a standalone file, open in browser, right-click canvas → "Save image as":

```html
<!DOCTYPE html>
<html>
<head>
    <title>Social Preview Generator</title>
</head>
<body>
    <canvas id="canvas" width="1200" height="630"></canvas>
    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        
        // Gradient background (your brand colors)
        const gradient = ctx.createLinearGradient(0, 0, 1200, 630);
        gradient.addColorStop(0, '#10b981');
        gradient.addColorStop(1, '#059669');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 1200, 630);
        
        // White overlay for text
        ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
        ctx.fillRect(100, 150, 1000, 330);
        
        // Title
        ctx.fillStyle = '#1f2937';
        ctx.font = 'bold 72px system-ui, -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('💰 Tax Budget Allocator', 600, 280);
        
        // Subtitle
        ctx.font = '48px system-ui, -apple-system, sans-serif';
        ctx.fillStyle = '#6b7280';
        ctx.fillText('Where Would You Spend', 600, 360);
        ctx.fillText('Your Tax Dollars?', 600, 420);
        
        // Domain
        ctx.font = 'bold 32px system-ui, -apple-system, sans-serif';
        ctx.fillStyle = '#10b981';
        ctx.fillText('tadpollster.com', 600, 540);
    </script>
</body>
</html>
```

## After Creating the Image

1. **Place it in the static directory:**
   ```bash
   mkdir -p allocator/static
   cp social-preview.png allocator/static/
   ```

2. **Collect static files (for production):**
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Update `do-app-spec.yaml` if needed** to ensure static files are served

4. **Deploy:**
   ```bash
   git add .
   git commit -m "Add social media preview image"
   git push origin main
   ```

5. **Verify:** Check the validators above to see your card preview

## What the Meta Tags Do

When someone shares `tadpollster.com` on:
- **Twitter/X:** Shows large image card with title, description, and preview
- **Facebook:** Shows rich preview with image
- **LinkedIn:** Shows professional card preview
- **Slack/Discord:** Shows embedded preview
- **iMessage:** Shows rich link preview

The tags are also customizable per page using Django template blocks!
