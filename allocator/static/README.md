# Static Files Directory

## Social Media Preview Image

Place your `social-preview.png` (1200×630px) in this directory.

### To Generate:
1. Open `generate_social_preview.html` in your browser (from project root)
2. Click "Download Image" button
3. Save as `social-preview.png` in this directory
4. Run `python manage.py collectstatic --noinput`
5. Deploy

### Current Status:
- [ ] social-preview.png (needed for social media cards)

The meta tags in `base.html` reference: `https://tadpollster.com/static/social-preview.png`
