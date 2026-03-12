# OLIA 👋

![GitHub repo size](https://img.shields.io/github/repo-size/Olive-Soft-Company/OLIA-PROJECT)
![GitHub language count](https://img.shields.io/github/languages/count/Olive-Soft-Company/OLIA-PROJECT)
![GitHub top language](https://img.shields.io/github/languages/top/Olive-Soft-Company/OLIA-PROJECT)
![GitHub last commit](https://img.shields.io/github/last-commit/Olive-Soft-Company/OLIA-PROJECT?color=red)

![OLIA Banner](./banner.png)

**OLIA is a governed enterprise AI workspace that activates internal knowledge and simplifies daily work.**  
It provides a **single secure entry point** to company information (documents, procedures, business tools, APIs), enabling teams to get **operational answers in natural language**, while enforcing **strict access rights** and **AI governance**.

> **The challenge is not to have more tools — it’s to better exploit existing information.**

**Demo:** https://olive-soft.atlassian.net/wiki/x/AQD9Rg

---

## Key Features of OLIA ⭐

- 🧠 **Knowledge Activation (RAG)**  
- 🔎 **Natural Language Search**  
- 🧩 **Native Integrations** (OneDrive, SharePoint, Confluence, Jira, APIs)  
- 🛡️ **Governance & Security (RBAC, SSO)**  
- ⚙️ **AI Orchestration Across Multiple Providers**  
- 🧰 **Tools & Automations**  
- 🗂️ **Conversation Organization**  
- 📊 **Usage Tracking & Governance Controls**  
- ☁️ **Production-ready Deployment Options**  
- 🌐 **Multilingual Experience**  

---

## How to Install 🚀  
> Local development environment (backend + frontend + build).

---

# 🔧 Backend Installation (Port 8080)

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch backend API
uvicorn olia.main:app --reload --host 0.0.0.0 --port 8080

# 🎨 Frontend Installation (Port 5173)
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# 🔧 Frontend Production Build

cd frontend

npm install
npm run build
