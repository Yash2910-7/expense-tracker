# Smart Spend AI — Intelligent Wealth Management Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.14%2B-blue.svg)](https://www.python.org/)
[![Flask Version](https://img.shields.io/badge/Flask-3.1%2B-green.svg)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-blue.svg)](https://www.postgresql.org/)

Smart Spend AI is a modern, production-ready, AI-powered wealth tracking and forecasting dashboard. Designed like a high-end fintech SaaS platform, it helps users analyze cash flows, configure category budgets, track recurring bills, and use machine learning to forecast future spending habits.

---

## 🏗️ System Architecture

```mermaid
graph TD
    Client[Web Browser - HTML5/CSS3/JS/Chart.js]
    FlaskServer[Flask Web Server - app.py]
    Auth[JWT Auth & Google OAuth Blueprint]
    DB[SQLAlchemy ORM - PostgreSQL/SQLite Fallback]
    Predictor[ML Module - RandomForestRegressor]
    Anomaly[ML Module - IsolationForest]
    Reports[ReportLab PDF & Matplotlib Charts]
    Emails[SMTP & Simulated Logger]

    Client -->|HTTP/REST APIs| FlaskServer
    FlaskServer --> Auth
    FlaskServer --> DB
    FlaskServer --> Predictor
    FlaskServer --> Anomaly
    FlaskServer --> Reports
    FlaskServer --> Emails
```

---

## ✨ Features Checklist

### 🔒 Security & Authentication
- **JWT Authentication**: Encrypted cookies issue JWT access tokens for stateless session tracking.
- **OTP Verification & Password Recovery**: Automated email/log OTP token dispatch for secure forgot-password flows.
- **Strong Passwords Validation**: Custom regex checkers verifying length, numbers, symbols, and letter cases.
- **Google OAuth Simulation**: consent sandbox page to sign in without developers key requirements.

### 💰 Cash Flow & Budgeting
- **Expense CRUD**: Log categorizations with receipt attachments (PNG, JPG, PDF) with drag-drop style.
- **Income Tracking**: Log revenue streams (Salary, Freelancing, Business, Investments, Other).
- **Advanced Filtering**: Live queries parsing description keywords, category tags, amounts, and dates.
- **Category Budget Planner**: Proportional 50/30/20 budget helper and budget warning.
- **Multi-currency Translate**: Convert and display dashboards dynamically in **₹ INR, $ USD, € EUR, or £ GBP**.

### 🔄 Bill Scheduler
- **Recurring Expenses**: Post Daily, Weekly, or Monthly automated charges (Netflix, Rent, EMIs).
- **Dynamic Posting Check**: Checks and auto-posts outstanding items upon user dashboard load.

### 🧠 Machine Learning Engine
- **Expense Prediction**: Uses `RandomForestRegressor` with lag indicators to forecast next week/month spending.
- **Anomaly Detection**: Employs `IsolationForest` to check and flag unusual transaction entries.
- **AI Insights & Health Scores**: Calculates 0-100 financial health scores and yields recommendations.
- **Challenges**: Gamified savings challenges (e.g. No-Spend Weekend) to encourage savings.

### 📊 Export Center
- **CSV Spreadsheets**: Exports transactional grids for ledger spreadsheets.
- **Adobe PDF Audits**: Generates professional PDFs with matplotlib charts, income grids, and savings milestones.

---

## 🛠️ Installation & Configuration

### 1. Prerequisites
- **Python 3.10+** (Compiled on Python 3.14)
- **PostgreSQL** service active (Falls back to SQLite dynamically if PostgreSQL is offline).

### 2. Setup Workspace & Virtual Environment
```bash
git clone https://github.com/your-username/smart-spend-ai.git
cd smart-spend-ai
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (`.env`)
Create a `.env` file in the root directory:
```env
SECRET_KEY=your_super_secret_session_key
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/expense_tracker

# Optional SMTP Details (If blank, emails write to reports/simulated_emails.log)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SENDER_EMAIL=your_email@gmail.com

# Optional Google Sign-In details
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### 5. Launch Server
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000`.

---

## 📁 Repository Directory Structure

```
project/
├── app.py                     # App bootstrap context (auto-creates databases)
├── config.py                  # Environment loader & configuration class
├── requirements.txt           # App dependencies
├── models/                    # Database models (SQLAlchemy ORM)
│   ├── __init__.py
│   ├── user.py                # User entity
│   ├── expense.py             # Expense ledger entries
│   ├── income.py              # Income streams
│   ├── savings.py             # Target goals milestones
│   └── recurring.py           # Bill schedulers
├── routes/                    # Flask Controller Blueprints
│   ├── auth.py                # Auth (Register, login, OTP, Mock Google OAuth)
│   ├── dashboard.py           # Core summaries and scheduler actions
│   ├── expenses.py            # Expense ledger CRUD
│   ├── income.py              # Income streams CRUD
│   ├── savings.py             # Goal tracking predictions
│   ├── recurring.py           # Scheduler settings
│   ├── reports.py             # Document downloads (PDF/CSV)
│   └── api.py                 # REST endpoints
├── services/                  # Business logic services
│   ├── email_service.py       # SMTP alerts & logging mock
│   └── receipt_service.py     # Receipt validator & file storage
├── ml/                        # Machine Learning Module
│   ├── spending_predictor.py  # RandomForestRegressor forecasting
│   ├── anomaly_detector.py    # IsolationForest anomaly flags
│   └── insights_generator.py  # Financial health calculations
├── templates/                 # Jinja2 HTML Viewports
├── static/                    # Asset bundles (style sheets, JS actions)
├── uploads/                   # Receipt storage folder
└── reports/                   # Compiled reports and logs output folder
```

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more details.