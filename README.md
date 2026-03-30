# 🎓 Student Platform — AI-Powered Career Tools

All features in a single Flask app at `http://localhost:5000`.

## Features

| Feature | FAB | Description |
|---------|-----|-------------|
| **Opportunity Finder** | Main page | 3-agent AI pipeline — hackathons, internships, scholarships |
| **AI Daily** | 🗞 AI Daily | Automated news engine — RSS feeds + Groq LLaMA summarization, daily insights |
| **Resume Builder** | 📄 Resume AI | Full-screen editor, 3 templates, live preview, PDF export |
| **Menti AI** | 💜 Menti AI | Gemini-powered empathetic voice companion |
| **Nexus Interviewer** | 🤖 Interview Prep | Groq-powered AI technical interviewer |

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
# Copy .env.example → .env and add GROQ_API_KEY
python app.py
# → http://localhost:5000
```

**Windows:** `start.bat`

---

## 🔑 API Keys

| Key | Get it at | Used for |
|-----|-----------|---------|
| `GROQ_API_KEY` | console.groq.com | Opportunity Finder · AI Daily · Nexus |
| Gemini API Key | aistudio.google.com | Menti AI (enter in-app) |

---

## 📁 Structure

```
/
├── app.py              ← Flask backend (all API routes)
├── agents.py           ← Opportunity Finder AI agents
├── requirements.txt    ← Python deps (includes feedparser)
├── templates/
│   └── index.html      ← Single-page app (all 5 features)
└── output/
    ├── ai_daily/       ← AI Daily newsletters (JSON) + subscriptions
    └── *.json          ← Opportunity Finder reports
```
