# ONA Quality Dashboard - Online Deployment Package

🎉 **Your dashboard is ready to deploy online and be accessible to everyone!**

## 📦 What's Included

This package contains everything you need to deploy your ONA Quality Dashboard online:

- ✅ `app.py` - Flask web application with auto-refresh
- ✅ `ona_quality_dashboard.py` - Dashboard generator
- ✅ `dashboard_config.json` - Configuration file
- ✅ `requirements.txt` - Python dependencies
- ✅ `render.yaml` - Render.com deployment config
- ✅ `Procfile` - Heroku deployment config
- ✅ `DEPLOYMENT_GUIDE.md` - Detailed deployment instructions

## 🚀 Quick Deploy (5 Minutes)

### Option 1: Deploy to Render.com (Recommended - Free)

1. **Download all files** to your computer

2. **Create a GitHub repository:**
   ```bash
   git init
   git add .
   git commit -m "ONA Dashboard"
   ```

3. **Push to GitHub:**
   - Create a new repository on github.com
   - Follow GitHub's instructions to push your code

4. **Deploy on Render:**
   - Go to [render.com](https://render.com)
   - Sign up (free account)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Click "Create Web Service"
   - Wait 3-5 minutes ⏳

5. **Done!** 🎉 Your dashboard will be live at:
   ```
   https://ona-quality-dashboard.onrender.com
   ```

### Option 2: Deploy to Heroku

```bash
# Install Heroku CLI first
heroku login
heroku create ona-dashboard
git push heroku main
```

Your dashboard will be live at: `https://ona-dashboard.herokuapp.com`

## 🔧 Configuration

### Your ONA API Credentials

The dashboard is pre-configured with your ONA credentials:
- **API URL:** https://api.ona.io/api/v1/data/864832
- **API Token:** 9cbc65f1c34ff5a3623cdac41043b788014992c0

### Security Best Practice

For production deployment, use environment variables:

**On Render:**
1. Go to your web service dashboard
2. Environment → "Add Environment Variable"
3. Add:
   - Key: `ONA_API_TOKEN`
   - Value: `9cbc65f1c34ff5a3623cdac41043b788014992c0`

**On Heroku:**
```bash
heroku config:set ONA_API_TOKEN=9cbc65f1c34ff5a3623cdac41043b788014992c0
```

## 🧪 Test Locally First

Before deploying, test on your computer:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Open browser to:
http://localhost:5000
```

## 📊 Dashboard Features

Once deployed, your dashboard will have:

### 1. Main Dashboard (`/`)
- **Auto-refreshes every hour** with latest ONA data
- Interactive visualizations:
  - Completion rates by district
  - Interview duration analysis
  - Missing data patterns
  - GPS coordinate verification
  - Daily submission trends
- Last update timestamp displayed

### 2. Manual Update (`/update`)
- Trigger immediate data refresh
- Useful for checking latest submissions

### 3. API Endpoints
- `/api/status` - Dashboard status and health
- `/api/metrics` - Get metrics as JSON
- `/api/update` - Trigger update (POST request)
- `/health` - Health check endpoint
- `/download/report` - Download Excel report

## 🔄 Auto-Update Settings

The dashboard automatically:
- Fetches new data from ONA every hour
- Regenerates all visualizations
- Refreshes the browser view

**To change update frequency**, edit `app.py`:
```python
REFRESH_INTERVAL = 3600  # Change to desired seconds
```

## 📱 Sharing Your Dashboard

Once deployed, share the URL with your team:

```
Your Dashboard: https://your-app-name.onrender.com
```

**Tips:**
- Bookmark for quick access
- Create QR code for mobile users
- Share specific pages:
  - `/` - Main dashboard
  - `/update` - Manual update page
  - `/download/report` - Download report

## 🔒 Security Features

1. **API Token Protection:**
   - Store tokens in environment variables
   - Never commit tokens to GitHub
   - Rotate tokens regularly

2. **Optional Authentication:**
   To add password protection, see `DEPLOYMENT_GUIDE.md`

## 📋 Deployment Checklist

Before deploying:
- ✅ All files downloaded
- ✅ Git repository initialized
- ✅ GitHub account created
- ✅ Render.com or Heroku account created
- ✅ ONA API credentials verified
- ✅ Local testing completed (optional)

## 🐛 Troubleshooting

### "No Data Available" Error
**Solution:** 
- Verify ONA API token is correct
- Check form ID (864832) is accessible
- Ensure API token has read permissions

### Dashboard Not Updating
**Solution:**
- Check logs on hosting platform
- Verify API credentials are set
- Try manual update at `/update`

### Slow Performance
**Solution:**
- Upgrade hosting plan (free tier may be slow)
- Reduce refresh interval
- Check ONA data size

### 404 Error
**Solution:**
- Wait 2-3 minutes for initial deployment
- Check deployment logs for errors
- Verify all files were committed to git

## 📖 Detailed Documentation

For more detailed information:
- **DEPLOYMENT_GUIDE.md** - Complete deployment instructions
- **README.md** - Original dashboard documentation
- **QUICKSTART.md** - Quick start guide

## 🆘 Need Help?

1. **Check the logs:**
   - Render: Dashboard → Logs tab
   - Heroku: `heroku logs --tail`

2. **Verify setup:**
   - Go to `/health` endpoint
   - Check `/api/status` for dashboard status

3. **Common issues:**
   - Wrong API credentials → Update environment variables
   - Missing dependencies → Check requirements.txt
   - Build failed → Review deployment logs

## 🎯 Next Steps

After deployment:

1. ✅ Test your live dashboard
2. ✅ Share URL with team
3. ✅ Set up environment variables for security
4. ✅ Monitor daily during data collection
5. ✅ Export quality reports regularly
6. ✅ Update thresholds after pilot data

## 💰 Hosting Costs

**Free Options:**
- **Render.com:** Free tier (750 hours/month)
  - Auto-sleeps after 15 min inactivity
  - 512MB RAM
  - Sufficient for small teams

- **Heroku:** Free tier available
  - Similar to Render
  - Good documentation

**Paid Options (for heavy use):**
- Render: $7/month (always on, more resources)
- Heroku: $7/month (Hobby tier)
- AWS/Google Cloud: Pay-as-you-go

## ✨ Success!

Your ONA Quality Dashboard is now ready for deployment! 

**In 5 minutes, you'll have:**
- ✅ A live, public dashboard
- ✅ Automatic hourly updates from ONA
- ✅ Accessible to your entire team
- ✅ No manual data exports needed

---

**Questions?** Check DEPLOYMENT_GUIDE.md for detailed instructions.

**Ready to deploy?** Follow the "Quick Deploy" steps above! 🚀
