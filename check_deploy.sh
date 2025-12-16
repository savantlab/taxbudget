#!/bin/bash
# Quick deployment status checker

APP_ID="3b89d417-366d-43eb-908b-eacbb4f519dc"

echo "📊 Checking deployment status..."
echo ""

# Get latest deployment
LATEST=$(doctl apps list-deployments $APP_ID | head -2 | tail -1)
DEPLOYMENT_ID=$(echo "$LATEST" | awk '{print $1}')
PHASE=$(echo "$LATEST" | awk '{print $4}')
PROGRESS=$(echo "$LATEST" | awk '{print $3}')

echo "Latest Deployment: $DEPLOYMENT_ID"
echo "Phase: $PHASE"
echo "Progress: $PROGRESS"
echo ""

# If active, show the app URL
if [ "$PHASE" == "ACTIVE" ]; then
    echo "✅ Deployment is ACTIVE!"
    echo ""
    APP_INFO=$(doctl apps get $APP_ID -o json)
    LIVE_URL=$(echo "$APP_INFO" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data[0].get('live_url', 'No URL'))" 2>/dev/null || echo "No URL yet")
    echo "🌐 App URL: $LIVE_URL"
elif [ "$PHASE" == "ERROR" ]; then
    echo "❌ Deployment has errors"
    echo ""
    echo "Recent error logs:"
    doctl apps logs $APP_ID --deployment $DEPLOYMENT_ID --type deploy 2>&1 | grep -i "error\|failed" | tail -5
elif [ "$PHASE" == "DEPLOYING" ] || [ "$PHASE" == "BUILDING" ]; then
    echo "⏳ Deployment in progress..."
fi
