# Deploy (Render / Railway)

GitHub only stores **code**. It does **not** run your Flask website.
A Windows `venv` folder also will **not** work on Linux hosting — never commit it.

## Why the site showed “text”

Usually one of these:

1. You opened the **GitHub repo** (README / source) instead of a live app URL  
2. You used **GitHub Pages** (static only — cannot run Flask)  
3. Deploy used the wrong start command / missing `gunicorn`  
4. Processed data was missing on the server

## Deploy on Render (recommended)

1. Push this repo to GitHub (already done).  
2. Go to https://render.com → **New** → **Web Service**.  
3. Connect `YASH12-byte/EV`.  
4. Settings:

| Field | Value |
|-------|--------|
| Runtime | Python 3 |
| Build command | `pip install -r requirements-deploy.txt` |
| Start command | `gunicorn run:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120` |
| Instance | Free |

5. Create Web Service and wait for the green **Live** URL, e.g.  
   `https://ev-forecast-xxxx.onrender.com`

6. Open that URL (not github.com). First load on free tier may take ~1 minute (cold start).

## Local website

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-deploy.txt
python run.py
```

Open http://127.0.0.1:5000

## Recreate venv after clone (do not commit venv)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
