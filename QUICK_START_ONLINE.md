# 🚀 DEPLOY YOUR ONA DASHBOARD ONLINE - QUICK START

## ⚡ 5-Minute Deployment to Make Your Dashboard Accessible to Everyone

Your ONA Quality Dashboard is ready to go online! Follow these simple steps:

---

## 📥 STEP 1: Download All Files (30 seconds)

Download these files to a folder on your computer:
- ✅ `app.py`
- ✅ `ona_quality_dashboard.py`
- ✅ `dashboard_config.json`
- ✅ `requirements.txt`
- ✅ `render.yaml`
- ✅ `Procfile`
- ✅ `.gitignore`

---

## 🌐 STEP 2: Deploy to Render.com (3 minutes)

### A. Create GitHub Repository

```bash
# Open terminal/command prompt in your folder
cd path/to/your/dashboard/folder

# Initialize git
git init
git add .
git commit -m "ONA Dashboard Initial Commit"
```

### B. Push to GitHub

1. Go to [github.com](https://github.com)
2. Click "New repository"
3. Name it: `ona-dashboard`
4. Don't initialize with README
5. Copy the commands shown and run them:

```bash
git remote add origin https://github.com/YOUR_USERNAME/ona-dashboard.git
git branch -M main
git push -u origin main
```

### C. Deploy on Render

1. Go to [render.com](https://render.com)
2. Click "Sign Up" (use your GitHub account)
3. Click "New +" → "Web Service"
4. Click "Connect" next to your `ona-dashboard` repository
5. Render auto-detects settings from `render.yaml`
6. Click "Create Web Service"
7. ⏳ Wait 3-5 minutes for deployment

### D. 🎉 Done!

Your dashboard is now live at:
```
https://ona-dashboard-XXXX.onrender.com
```

(Render will show you the exact URL)

---

## ✅ STEP 3: Test Your Dashboard (1 minute)

1. Click the URL from Render
2. You should see: "Dashboard generating..."
3. Wait 30-60 seconds for first data fetch
4. Dashboard appears with all your ONA data!

---

## 🔄 How It Works

Your dashboard now automatically:
- ✅ Fetches data from ONA every hour
- ✅ Updates all visualizations
- ✅ Refreshes the page
- ✅ Is accessible 24/7 to anyone with the link

---

## 🔐 SECURITY: Protect Your API Token

**IMPORTANT:** For production use:

1. Go to Render Dashboard → Your Service
2. Click "Environment"
3. Add Environment Variable:
   - **Key:** `ONA_API_TOKEN`
   - **Value:** `9cbc65f1c34ff5a3623cdac41043b788014992c0`
4. Update `app.py` to use environment variable:

```python
import os
ONA_API_TOKEN = os.environ.get('ONA_API_TOKEN', 'your-token-here')
```

5. Commit and push changes - Render auto-deploys

---

## 📱 Share Your Dashboard

Share this link with your team:
```
https://your-dashboard-name.onrender.com
```

**Pages available:**
- `/` - Main dashboard
- `/update` - Manual update page
- `/api/status` - Dashboard status
- `/download/report` - Download Excel report

---

## ⚙️ Customization

### Change Update Frequency

Edit `app.py`:
```python
REFRESH_INTERVAL = 3600  # 3600 = 1 hour, 1800 = 30 min
```

### Change Dashboard Title

Edit `ona_quality_dashboard.py`:
```python
title={'text': 'Your Organization - Data Quality Dashboard'}
```

### Update Thresholds

Edit `dashboard_config.json`:
```json
{
    "min_duration": 30,
    "max_duration": 120
}
```

---

## 🐛 Troubleshooting

### Dashboard shows "No Data Available"
**Fix:** Check your ONA API credentials in `app.py`

### Dashboard not updating
**Fix:** Go to `/update` page and click "Update Dashboard Now"

### Render service "sleeping"
**Note:** Free tier sleeps after 15 min inactivity. First visit takes 30-60 sec to wake up.

**Upgrade to paid tier ($7/month) for:**
- Always-on service
- Faster response
- More resources

---

## 💰 Cost

**Free Option (Render Free Tier):**
- ✅ 750 hours/month (more than enough for 24/7)
- ✅ Auto HTTPS
- ✅ Auto deploy on git push
- ⚠️ Sleeps after 15 min inactivity

**Paid Option ($7/month):**
- ✅ Always on
- ✅ 512MB RAM → 2GB RAM
- ✅ No sleep

---

## 🎯 What You Get

After deployment, you have:

✅ **Live Dashboard** - Accessible 24/7 from anywhere
✅ **Auto-Updates** - Fetches ONA data every hour automatically
✅ **No Manual Work** - No more CSV exports or manual updates
✅ **Team Access** - Share one link with everyone
✅ **Quality Monitoring** - Real-time data quality metrics
✅ **Excel Reports** - Download detailed reports anytime

---

## 📊 Dashboard Features

Your live dashboard includes:

1. **Completion Rates by District**
2. **Interview Duration Analysis**
3. **Missing Data Patterns**
4. **GPS Verification Map**
5. **Daily Submission Trends**
6. **Summary Statistics**
7. **Quality Alerts**
8. **Excel Report Export**

---

## 🔄 Updating Your Dashboard Code

When you make changes:

```bash
git add .
git commit -m "Updated dashboard"
git push origin main
```

Render automatically detects and deploys your changes!

---

## 🆘 Need Help?

### Quick Checks:
1. Visit `/health` - Should show "healthy"
2. Visit `/api/status` - Shows last update time
3. Check Render logs - Dashboard → Logs tab

### Common Issues:

**Build Failed:**
- Check Render logs for specific error
- Ensure all files were committed to git

**API Error:**
- Verify ONA form ID: 864832
- Check API token is correct
- Ensure token has read permissions

---

## 📖 More Information

- **DEPLOYMENT_GUIDE.md** - Detailed deployment instructions
- **README_DEPLOY.md** - Complete documentation

---

## ✨ Success Checklist

- ✅ Files downloaded
- ✅ Git repository created
- ✅ Pushed to GitHub
- ✅ Deployed on Render
- ✅ Dashboard accessible online
- ✅ Team has access to URL
- ✅ Auto-updates working

---

## 🎉 Congratulations!

Your ONA Quality Dashboard is now live and accessible to everyone!

**Your Next Steps:**
1. Share the URL with your team
2. Bookmark the dashboard
3. Check it daily during data collection
4. Download quality reports weekly
5. Update thresholds after pilot data collection

---

**Dashboard URL:** https://your-dashboard-name.onrender.com

**Questions?** Check the DEPLOYMENT_GUIDE.md or Render documentation.

**Happy Monitoring! 📊✨**
