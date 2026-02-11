# OLIA 👋

![GitHub stars](https://img.shields.io/github/stars/<org>/<repo>?style=social)
![GitHub forks](https://img.shields.io/github/forks/<org>/<repo>?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/<org>/<repo>?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/<org>/<repo>)
![GitHub language count](https://img.shields.io/github/languages/count/<org>/<repo>)
![GitHub top language](https://img.shields.io/github/languages/top/<org>/<repo>)
![GitHub last commit](https://img.shields.io/github/last-commit/<org>/<repo>?color=red)
[![Discord](https://img.shields.io/badge/Discord-OLIA-blue?logo=discord&logoColor=white)](<your_discord_invite>)
[![](https://img.shields.io/static/v1?label=Contact&message=Sales&logo=mail.ru&color=%2300DDDC)](mailto:<sales@your-company.com>)

![OLIA Banner](./banner.png)

**OLIA is a governed enterprise AI workspace that activates internal knowledge and simplifies daily work.**  
It provides a **single secure entry point** to company information (documents, procedures, business tools, APIs), enabling teams to get **operational answers in natural language**, while enforcing **strict access rights** and **AI governance**.

> **The challenge is not to have more tools — it’s to better exploit existing information.**

![OLIA Demo](./demo.png)

> [!TIP]  
> **Looking for an Enterprise Plan?** – **Contact our Sales Team**
>
> Get **SLA support**, **LTS versions**, **custom integrations**, and **production hardening**.

For more information, see our **internal documentation** or the project docs in this repository.

---

## Key Features of OLIA ⭐

- 🧠 **Knowledge Activation (RAG)**: Search and use internal knowledge in conversations (documents, procedures, knowledge bases) to produce more reliable, contextual answers.

- 🔎 **Natural Language Search**: Ask questions as you speak — OLIA retrieves the relevant content and returns actionable answers.

- 🧩 **Native Integrations**: Connectors for enterprise tools such as **OneDrive/SharePoint**, **Confluence**, **Jira**, and **business APIs** (depending on your package).

- 🛡️ **Security & Governance by Design**: Strict access-right enforcement (“who can access what”), RBAC, and enterprise-grade controls aligned with your SI policies.

- ⚙️ **Multi-Provider Orchestration**: Plug different AI engines (text or multimodal) and route tasks based on needs and governance rules.

- 🧰 **Tools & Automation**: Execute actions (ticket creation, searches, data lookup, summarization workflows) directly from chat through server-side tools.

- 🗂️ **Conversation Organization**: Organize work using folders/tags for faster reuse and collaboration (if enabled).

- 📊 **Usage Tracking**: Monitor usage and adoption; support governance and cost control (optional module).

- ☁️ **Production-ready Deployments**: Run on-prem or in cloud, with Docker/Kubernetes patterns, scalable storage backends, and observability options.

- 🌐🌍 **Multilingual Support**: Use OLIA in your preferred language with i18n support.

---

We are grateful to everyone contributing to OLIA and helping teams work faster with secure, governed AI.

## How to Install 🚀

> [!IMPORTANT]
> The steps below are intended for **local development**. For production, use the recommended Docker/Kubernetes deployment with persistent storage and secrets management.

---

### Backend (Development) — Port 8080

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate
# Windows (PowerShell)
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch API
uvicorn open_webui.main:app --reload --host 0.0.0.0 --port 8080
