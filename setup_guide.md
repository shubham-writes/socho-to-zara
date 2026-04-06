# 🧩 RiddleAnPuzzle — Setup Guide

Complete guide to get your automated Instagram Reels pipeline running.

---

## 📋 Prerequisites

- **Python 3.10+** installed
- **ImageMagick** (required by MoviePy for text rendering)
- **FFmpeg** (usually bundled with MoviePy, but good to have)

---

## Step 1: Install Python Dependencies

```powershell
cd c:\Users\Shubham\RiddleAnPuzzle
pip install -r requirements.txt
```

---

## Step 2: Install ImageMagick

MoviePy needs ImageMagick for text overlay rendering.

1. Download from: https://imagemagick.org/script/download.php#windows
2. During installation, **check** "Install legacy utilities (e.g. convert)"
3. **Check** "Add application directory to your system PATH"
4. Verify installation:
   ```powershell
   magick --version
   ```

> **Note**: If MoviePy can't find ImageMagick, set the environment variable:
> ```powershell
> $env:IMAGEMAGICK_BINARY = "C:\Program Files\ImageMagick-7.x.x-Q16-HDRI\magick.exe"
> ```

---

## Step 3: Download the Font

Download **Montserrat Bold** (free Google Font):

1. Go to: https://fonts.google.com/specimen/Montserrat
2. Download the family
3. Extract `Montserrat-Bold.ttf`
4. Place it in: `c:\Users\Shubham\RiddleAnPuzzle\fonts\Montserrat-Bold.ttf`

---

## Step 4: Get API Keys

### Pexels API (Background Videos) — Required
1. Create a free account at: https://www.pexels.com/api/
2. Go to your profile → API Keys
3. Copy your API key

### Google AI Studio (Riddle Generation) — Optional
1. Go to: https://aistudio.google.com/app/apikey
2. Create a new API key
3. Free tier: 1,000 requests/day

> If you skip this, the pipeline uses the built-in bank of 30 riddles.

---

## Step 5: Configure Environment

1. Copy the template:
   ```powershell
   copy .env.example .env
   ```

2. Edit `.env` and fill in your keys:
   ```
   PEXELS_API_KEY=your_pexels_key_here
   GEMINI_API_KEY=your_gemini_key_here    # optional
   ```

---

## Step 6: Test with a Dry Run

```powershell
python pipeline.py --dry-run
```

This will:
- Generate a riddle
- Create TTS audio
- Fetch a background video
- Assemble the final Reel
- Save it to `output/reels/` (without posting to Instagram)

---

## Step 7: Set Up Instagram Posting

### 7a. Convert to Business/Creator Account
1. Open Instagram → Settings → Account → Switch to Professional Account
2. Choose **Creator** or **Business**
3. Connect to a **Facebook Page**

### 7b. Create a Meta Developer App
1. Go to: https://developers.facebook.com/
2. Create a new app → Choose "Business" type
3. Add the **Instagram Graph API** product
4. Under Instagram → Basic Display, note your **App ID** and **App Secret**

### 7c. Get a Long-Lived Access Token
1. In the Meta Developer dashboard, go to Graph API Explorer
2. Select your app
3. Request permissions: `instagram_basic`, `instagram_content_publish`, `pages_read_engagement`
4. Generate a **User Access Token**
5. Exchange for a **Long-Lived Token** (60 days):
   ```
   GET https://graph.facebook.com/v21.0/oauth/access_token?
     grant_type=fb_exchange_token&
     client_id={app-id}&
     client_secret={app-secret}&
     fb_exchange_token={short-lived-token}
   ```
6. Get your **Instagram User ID**:
   ```
   GET https://graph.facebook.com/v21.0/me/accounts?access_token={token}
   ```
   Then:
   ```
   GET https://graph.facebook.com/v21.0/{page-id}?fields=instagram_business_account&access_token={token}
   ```

### 7d. Host Videos Publicly
Instagram requires videos at a public URL. Options:
- **Firebase Storage** (free tier: 5GB storage, 1GB/day download)
- **Cloudflare R2** (free tier: 10GB storage)
- **ngrok** (free tunnel to serve local files)

Update `.env`:
```
IG_ACCESS_TOKEN=your_long_lived_token
IG_USER_ID=your_instagram_user_id
VIDEO_HOST_BASE_URL=https://your-hosting-url.com/reels/
```

---

## Step 8: Schedule Daily Runs

### Option A: Windows Task Scheduler (Recommended)
1. Open Task Scheduler
2. Create Basic Task → "RiddleAnPuzzle Daily"
3. Trigger: Daily at your preferred time (e.g., 10:00 AM)
4. Action: Start a Program
   - Program: `python`
   - Arguments: `pipeline.py`
   - Start in: `c:\Users\Shubham\RiddleAnPuzzle`

### Option B: Python Scheduler
```powershell
python scheduler/daily_scheduler.py --time 10:00
```
(Keep this terminal window open)

---

## 🎯 Quick Reference

| Command | Description |
|---|---|
| `python pipeline.py --dry-run` | Generate video without posting |
| `python pipeline.py` | Full run: generate + post |
| `python pipeline.py --day 5` | Generate for specific day |
| `python scheduler/daily_scheduler.py` | Start daily auto-scheduler |
