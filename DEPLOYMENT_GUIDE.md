# ONA Dashboard - Online Deployment Guide

This guide will help you deploy your ONA Quality Dashboard online so it's accessible to everyone via a public URL.

## 🌐 Deployment Options

### Option 1: Render.com (Recommended - Free & Easy)

**Best for:** Quick deployment, free hosting, automatic HTTPS

#### Steps:

1. **Create a GitHub repository:**
   ```bash
   # Initialize git in your project folder
   git init
   git add .
   git commit -m "Initial commit - ONA Dashboard"
   
   # Create a new repository on GitHub and push
   git remote add origin https://github.com/YOUR_USERNAME/ona-dashboard.git
   git branch -M main
   git push -u origin main
   ```

2. **Deploy on Render:**
   - Go to [render.com](https://render.com) and sign up (free)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect the `render.yaml` configuration
   - Click "Create Web Service"
   - Wait 3-5 minutes for deployment

3. **Your dashboard will be live at:**
   ```
   https://ona-quality-dashboard.onrender.com
   ```

#### Render Configuration Details:
- **Free tier includes:**
  - 750 hours/month (enough for 24/7 operation)
  - Automatic HTTPS
  - Auto-deploy on git push
  - 512MB RAM
  
- **Note:** Free tier services sleep after 15 minutes of inactivity. First request may take 30-60 seconds to wake up.

---

### Option 2: Heroku (Alternative Free Option)

**Best for:** Simple deployment, good documentation

#### Steps:

1. **Install Heroku CLI:**
   ```bash
   # macOS
   brew tap heroku/brew && brew install heroku
   
   # Ubuntu/Debian
   curl https://cli-assets.heroku.com/install.sh | sh
   ```

2. **Deploy to Heroku:**
   ```bash
   # Login to Heroku
   heroku login
   
   # Create a new Heroku app
   heroku create ona-dashboard-YOUR-NAME
   
   # Deploy
   git init
   git add .
   git commit -m "Deploy ONA Dashboard"
   git push heroku main
   ```

3. **Your dashboard will be live at:**
   ```
   https://ona-dashboard-YOUR-NAME.herokuapp.com
   ```

---

## 📋 Pre-Deployment Checklist

Before deploying, ensure you have:

- ✅ Your ONA API credentials configured in `app.py`
- ✅ All required files in your project folder:
  - `app.py` (main Flask application)
  - `ona_quality_dashboard.py` (dashboard generator)
  - `dashboard_config.json` (configuration)
  - `requirements.txt` (dependencies)
  - `Procfile` (for Heroku)
  - `render.yaml` (for Render)
- ✅ Tested locally to ensure everything works

---

## 🧪 Local Testing Before Deployment

Test your dashboard locally first:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask app
python app.py

# Open browser to http://localhost:5000
```

---

## 🔒 Security Considerations

### Protect Your ONA API Token

Update `app.py` to use environment variables:

```python
import os

ONA_API_URL = os.environ.get('ONA_API_URL', 'https://api.ona.io/api/v1/data/864832')
ONA_API_TOKEN = os.environ.get('ONA_API_TOKEN')
```

Then set environment variables on your hosting platform:

**Render:**
- Dashboard → Environment → Add Environment Variable
- Key: `ONA_API_TOKEN`
- Value: `9cbc65f1c34ff5a3623cdac41043b788014992c0`

**Heroku:**
```bash
heroku config:set ONA_API_TOKEN=9cbc65f1c34ff5a3623cdac41043b788014992c0
```

---

## 🔄 Auto-Update Configuration

The dashboard automatically:
- Fetches data from ONA every hour
- Regenerates the dashboard
- Refreshes the browser view

To change the update interval, modify in `app.py`:
```python
REFRESH_INTERVAL = 3600  # Change to desired seconds (3600 = 1 hour)
```

---

## 📊 Dashboard Features

Once deployed, your dashboard will have:

1. **Main Dashboard** (`/`)
   - Interactive visualizations
   - Auto-refreshes every hour

2. **Manual Update** (`/update`)
   - Trigger immediate data refresh

3. **API Endpoints:**
   - `/api/status` - Check dashboard status
   - `/api/metrics` - Get metrics as JSON
   - `/health` - Health check

4. **Download Report** (`/download/report`)
   - Excel quality report

---

## 🐛 Troubleshooting

### Dashboard shows "Update in Progress"
- Wait 1-2 minutes for data fetch to complete
- Check logs on your hosting platform

### "No Data Available" Error
- Verify ONA API credentials are correct
- Check that form ID (864832) is accessible
- Ensure API token has read permissions

---

## 🎉 Quick Start (5 Minutes to Live Dashboard)

```bash
# 1. Setup git
git init
git add .
git commit -m "ONA Dashboard"

# 2. Create GitHub repo and push
git remote add origin https://github.com/YOUR_USERNAME/ona-dashboard.git
git push -u origin main

# 3. Deploy on Render
# - Go to render.com
# - New Web Service
# - Connect GitHub repo
# - Click "Create"

# 4. Done! Your dashboard is live in 3-5 minutes
```

Your dashboard should now be live and accessible to everyone! 🚀
