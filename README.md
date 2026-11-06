# 📱 Field Collections & Priority Operations Platform

> **Offline-first field collections and loan recovery platform featuring intelligent 0-100 priority scoring, RBI compliance hour restrictions, and manager analytics.**

---

## 🚀 Overview
The **Field Collections Platform** is an enterprise-grade web application optimized for field collection officers and team managers. It automates loan assignments by pincode and workload, ranks overdue accounts via an explainable scoring engine, enforces strict RBI telephony and messaging compliance hours (8:00 AM – 7:00 PM IST), and ensures seamless offline outcome synchronization.

---

## 📁 File Structure
```text
field-collections/
├── assets/
│   └── app-preview.png        # Application dashboard preview screenshot
├── static/
│   └── index.html             # Mobile-first frontend UI (Officer & Manager dashboards, bilingual, offline queue)
├── tests/
│   ├── conftest.py            # Test fixtures and database test setup
│   └── test_all.py            # Comprehensive backend unit & integration tests
├── .env.example               # Environment variables configuration template
├── .gitignore                 # Git ignore rules for virtualenvs, databases, and caches
├── app.py                     # FastAPI backend application, REST endpoints, and middleware
├── compliance.py              # RBI time-window compliance rules and threat-word filter
├── deployment.md              # Detailed local installation and production deployment guide
├── Field_Collections_TDD.pdf  # Technical Design Document (Architecture, Scoring, Back-test)
├── requirements.txt           # Python package dependencies
├── scoring.py                 # Explainable 0-100 heuristic priority scoring engine
└── seed.py                    # Initial database seed script with demo users and sample loans
```
## ✨ Key Features

### 🏢 **For Field Officers**
* **Prioritized Queue:** Dynamic 0–100 risk scoring with clear rationale chips (DPD, amount, broken promises).
* **Compliance Safeguards:** Hardware-blocks calls and SMS outside 8 AM – 7 PM IST to maintain strict regulatory compliance.
* **Offline-First Synchronization:** Actions queue securely on the device (`localStorage`) when offline and sync automatically upon reconnection without duplicates.
* **GPS Outcome Logging:** Automatically captures precise latitude and longitude metadata with outcomes (*Paid, Promise, Dispute, Not Reachable*).
* **Bilingual UI:** Instant English and Hindi language toggle.

### 📊 **For Managers**
* **Roll-Rate Analytics:** Real-time branch-level roll-rate tracking against portfolio targets (e.g., 16% threshold).
* **Weekly Scoring Back-Test:** Evaluates algorithm accuracy by comparing predicted risk tiers against actual 7-day recoveries (Gini 0.74).
* **CSV Import Engine:** Upload daily overdue loan exports with built-in data validation and auto-assignment.
* **Officer Activity Monitoring:** Tracks daily logged attempts and compliance blocks per officer.

---

## 🛠️ Tech Stack
* **Backend:** Python FastAPI, SQLAlchemy, SQLite
* **Frontend:** Mobile-first Vanilla HTML5, CSS3 (Tailwind-inspired custom classes), JavaScript (PWA Service Worker ready)
* **Testing:** Pytest / TestClient suite

---

## 🚀 Getting Started & Local Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/shreeversehub/field-collections.git](https://github.com/shreeversehub/field-collections.git)
   cd field-collections
