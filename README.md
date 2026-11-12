# TheScoutSystem

A football scouting and stat-tracking web app covering the top 5 European leagues. Search and filter players, view detailed stats and contract information, build a shortlist, find statistically similar players, generate league summary reports, and ask an AI assistant questions about the data.

Built as a full-stack project, starting from a university data management assignment (Swinburne University of Technology) and extended into a deployed portfolio piece.

**Live demo:** https://scoutsystem.vercel.app

---

## Before you click around (please read)

This project runs entirely on free hosting tiers, which comes with a few quirks:

- **The first load can take 30–60 seconds.** The backend (Render) and the database (TiDB Cloud) both go to sleep when idle. The first request wakes them up, and the backend also rebuilds its similar-player model on startup. After that first load, everything is fast. If the player list shows "Could not load players" straight away, wait a minute and refresh.
- **The AI Assistant might not work.** It uses Google's Gemini API on the free tier, which has strict rate limits and is sometimes overloaded ("too much activity" errors). If the assistant fails or returns an error, that's the API limit, not a bug in the app. Try again in a minute or two.

### Demo login

The admin area uses role-based access control. To try it:

| Username | Password |
|----------|----------|
| `admin`  | `1234`   |

This is a public demo account with no real data behind it.

---

## Features

- **Player search and filters** by name, league, club, nation, position and status, with sorting (e.g. highest market value)
- **Player profiles** with season stats, contract information (start and expiry dates, weekly wage, release clause) and scouting reports
- **Similar players**: a k-nearest-neighbours model finds players with comparable per-90 stats within the same position group, with a percentage similarity score, and can export the comparison to PDF
- **Shortlist** to save players, with CSV report generation
- **League summary reports** that can be generated and downloaded as CSV files
- **AI Assistant** (LangChain agent with Google Gemini) that answers questions using the database and scouting reports
- **Role-based access control** with a login page and an admin page

## How the similar-player model works

- Uses 2025/26 season stats for outfield players in the top 5 leagues with at least 900 minutes played
- Stats are converted to per-90 values, so playing time doesn't skew comparisons
- Each position group (defender, midfielder, attacker) uses its own set of relevant stats, which are standardised with `StandardScaler`
- Similarity is measured with cosine distance using scikit-learn's `NearestNeighbors`
- The models are built from the database when the backend starts and held in memory

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, Vite |
| Backend | Python, FastAPI |
| Relational database | MySQL-compatible (TiDB Cloud) for players, clubs, stats, contracts and users |
| Document database | MongoDB Atlas for scouting reports |
| ML | pandas, scikit-learn (k-NN) |
| AI assistant | LangChain, LangGraph, Google Gemini |
| Auth | bcrypt password hashing, session cookies |

## Architecture and hosting

```
Browser
   │
   ▼
Vercel  (React frontend, forwards /api/* to the backend)
   │
   ▼
Render  (FastAPI backend, Singapore region)
   │              │
   ▼              ▼
TiDB Cloud     MongoDB Atlas
(MySQL data)   (scouting reports)
```

The frontend proxies API calls through Vercel (`frontend/vercel.json`), so the browser only talks to one origin and session cookies work without cross-site settings. The backend and the SQL database are both in the Singapore region to keep query latency low.

## Repository layout

```
.
├── main.py                  # FastAPI app and routes
├── database.py              # MySQL connection pool and MongoDB client
├── adminLogin.py            # Login and role-based access routes
├── chatbot.py               # LangChain / Gemini assistant
├── SimilarPlayerModel.py    # k-NN similar-player model
├── requirements.txt
├── isrgrootx1.pem           # public root certificate for the TLS database connection
├── schemas/                 # SQL schema definitions
├── scripts/                 # data loading scripts
├── datasets/                # source data files
└── frontend/                # React app (Vite)
```

## Running it locally

### Prerequisites

- Python 3.12 or newer
- Node.js 18 or newer
- A MySQL-compatible database and a MongoDB database

### Backend

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Create a `.env` file in the project root:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=your_database
# Only needed for a cloud database that requires TLS (e.g. TiDB Cloud):
# DB_SSL_CA=isrgrootx1.pem

MONGODB_URI=your_mongodb_connection_string
MONGO_DB=scouting_system
MONGO_COLLECTION=scouting_reports

SESSION_SECRET=a_long_random_string
GOOGLE_API_KEY=your_gemini_api_key
```

The database tables are defined in `schemas/`, and the loading scripts in `scripts/` populate them from `datasets/`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on http://localhost:5173 and talks to the backend at http://localhost:8000.

## Deployment notes

- **Backend (Render):** build command `pip install -r requirements.txt`, start command `uvicorn main:app --host 0.0.0.0 --port $PORT`, with the environment variables above set in the dashboard
- **Frontend (Vercel):** root directory `frontend`, framework preset Vite
- **Databases:** TiDB Cloud (Starter tier) and MongoDB Atlas (free tier)

## Known limitations

- Free-tier cold starts (see the note at the top)
- Gemini free-tier rate limits can make the AI Assistant unreliable
- Only top 5 leagues have advanced stats

## Author

Lucas Jurgec, Bachelor of Computer Science (Professional), Swinburne University of Technology
