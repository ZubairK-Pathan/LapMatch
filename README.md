<div align="center">

# 💻 LapMatch

### AI-Powered Laptop Recommendation Engine

**Find your perfect laptop using natural language**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-lapmatch.zubairkhan.app-blue?style=for-the-badge&logo=azure)](https://lapmatch.zubairkhan.app)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Azure](https://img.shields.io/badge/Azure-Container%20Apps-0078D4?style=for-the-badge&logo=microsoftazure&logoColor=white)](https://azure.microsoft.com)
[![Cloudflare](https://img.shields.io/badge/Cloudflare-Workers-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)](https://workers.cloudflare.com)

</div>

---

## 🎯 What is LapMatch?

LapMatch lets you describe what you need in plain English and returns a ranked list of laptops that mathematically match your requirements. No more comparing spec sheets manually.

**Try it:** *"I'm a CS student who games on weekends, needs good battery, budget ₹80,000"*

LapMatch extracts your intent using an LLM, scores every laptop in its dataset against your priorities, and returns your best matches — along with a live market insights chart.

---

## ✨ Features

- 🗣️ **Natural Language Search** — Describe your needs in plain text, no forms or filters
- 🤖 **AI Intent Extraction** — LLM parses budget, performance needs, portability, and battery priority
- 📊 **Market Insights** — Interactive chart showing price vs. performance distribution
- ⚡ **Dual AI Fallback** — Google Gemini (primary) → Groq (fallback) for high availability
- 🌍 **Deployed on Azure** — UAE North region, Cloudflare CDN + SSL

---

## 🏗️ Architecture

```
User (Browser)
    │
    ▼  HTTPS (SSL via Cloudflare)
Cloudflare Edge  ──── Workers proxy (Host header rewrite)
    │
    ▼
Azure Container App  (UAE North)
    │
    ├── FastAPI Backend
    │       │
    │       ├── Stage 1: LLM Extraction
    │       │       ├── Google Gemini (primary)
    │       │       └── Groq gpt-oss-20b (fallback)
    │       │
    │       └── Stage 2: Scoring Algorithm
    │               └── Smartprix dataset (~2,000 laptops)
    │
    └── Vanilla HTML/CSS/JS Frontend
```

### Two-Stage AI Pipeline

1. **Extraction** — A small, fast LLM reads the user's free-text query and outputs a structured JSON object:
   ```json
   {"budget": 80000, "q_perf": "B", "q_port": "C", "q_batt": "C"}
   ```

2. **Scoring** — A deterministic algorithm scores every laptop in the dataset against those parameters and returns the top-ranked results.

This separation keeps the AI focused on what it does best (understanding intent) while the ranking logic stays auditable and consistent.

---

## 🛡️ Reliability: AI Fallback Chain

LapMatch never fully fails. Under high traffic or quota exhaustion, it degrades gracefully:

```
Google Gemini  →  Groq (gpt-oss-20b)  →  Default recommendations
  (primary)          (< 2s response)         (zero AI dependency)
```

**Why Groq?** Groq uses custom LPU (Language Processing Unit) silicon — purpose-built for LLM inference. At 20B parameters, response times are under 2 seconds even under load.

**Fail-fast logic:** Quota errors are detected immediately and the fallback is triggered without retry delays, avoiding the 30+ second hangs that retry-based approaches cause.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Google Gemini API key → [Get one here](https://aistudio.google.com)
- Groq API key → [Get one here](https://console.groq.com) *(optional, for fallback)*

### Local Setup

```bash
# Clone the repository
git clone https://github.com/ZubairK-Pathan/LapMatch.git
cd LapMatch

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY="your_gemini_key_here"
export GROQ_API_KEY="your_groq_key_here"  # optional

# Run the app
uvicorn app:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 🐳 Docker

```bash
# Build
docker build -t lapmatch .

# Run
docker run -p 8000:8000 \
  -e GEMINI_API_KEY="your_key" \
  -e GROQ_API_KEY="your_key" \
  lapmatch
```

---

## 📁 Project Structure

```
LapMatch/
├── app.py                  # FastAPI application, API routes, AI pipeline
├── models/
│   └── recommender.py      # Laptop scoring & ranking algorithm
├── data/
│   └── smartprix_laptop.csv  # Laptop dataset (~2,000 entries)
├── static/
│   ├── styles.css          # UI styles
│   └── script.js           # Frontend logic, API calls, Chart.js
├── templates/
│   └── index.html          # Main page template
├── tests/
│   └── test_app.py         # API endpoint tests
├── Dockerfile              # Container definition
├── requirements.txt        # Python dependencies
└── deploy_uae.sh           # Azure deployment script
```

---

## 🌐 Deployment

LapMatch runs on **Azure Container Apps** (UAE North region) behind **Cloudflare**.

### Infrastructure

| Layer | Technology | Purpose |
|---|---|---|
| SSL + CDN | Cloudflare | Free HTTPS for `.app` domain, DDoS protection |
| Proxy | Cloudflare Workers | Host header rewrite for Azure routing |
| Hosting | Azure Container Apps | Serverless containers, scales to zero |
| Registry | Azure Container Registry | Private Docker image storage |
| Region | UAE North | Gemini API region compatibility |

### Why this setup?

`.app` domains enforce HTTPS by browser policy (HSTS preloading). Azure Container Apps on student plans don't support custom domains. Cloudflare solves both: it issues the SSL certificate and proxies traffic to Azure. A lightweight Cloudflare Worker rewrites the `Host` header so Azure's routing layer accepts the request.

### Deploy your own

```bash
# 1. Build and push image to ACR
az acr build --registry <your-registry> --image lapmatch:latest .

# 2. Deploy to Container Apps
az containerapp create \
  --name lapmatch \
  --resource-group <your-rg> \
  --environment <your-env> \
  --image <your-registry>.azurecr.io/lapmatch:latest \
  --ingress external \
  --target-port 8000 \
  --secrets gemini-api-key=<key> groq-api-key=<key> \
  --env-vars GEMINI_API_KEY=secretref:gemini-api-key GROQ_API_KEY=secretref:groq-api-key
```

---

## 🔌 API Reference

### `POST /recommend`

Returns ranked laptop recommendations based on a natural language query.

**Request:**
```json
{
  "prompt": "CS student, light gaming, good battery, budget 80000 INR"
}
```

**Response:**
```json
{
  "extracted": {
    "budget": 80000,
    "q_perf": "B",
    "q_port": "C",
    "q_batt": "C"
  },
  "recommendations": [
    {
      "name": "ASUS VivoBook 15",
      "price": 74990,
      "score": 0.94,
      "specs": { ... }
    }
  ]
}
```

### `GET /market-insights`

Returns aggregated price vs. performance data for the market insights chart.

---

## 🛠️ Tech Stack

| Category | Technology |
|---|---|
| **Language** | Python 3.11 |
| **Framework** | FastAPI + Uvicorn |
| **AI (Primary)** | Google Gemini API |
| **AI (Fallback)** | Groq API (`openai/gpt-oss-20b`) |
| **Frontend** | Vanilla HTML, CSS, JavaScript |
| **Charts** | Chart.js |
| **Containerization** | Docker |
| **Cloud** | Azure Container Apps (UAE North) |
| **CDN / SSL** | Cloudflare |
| **Version Control** | GitHub |

---

## 📄 License

MIT License — feel free to fork, modify, and use this project.

---

<div align="center">

Built by [Zubairkhan Pathan](https://zubairkhan.app) · [Portfolio](https://zubairkhan.app) · [LapMatch Live](https://lapmatch.zubairkhan.app)

</div>
