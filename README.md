# CloudExam – Cloud-Based Online Examination System

CloudExam is a modular, high-performance web-based examination platform developed using **Python Flask**, **SQLAlchemy**, **SQLite**, **Bootstrap 5**, and **Chart.js**. It provides separate role-based portals for administrators to manage exams, MCQ questions, and view performance analytics, and for students to attend timed examinations with automatic evaluation and PDF result generation.

---

## 🚀 Key Features

* **Authentication & RBAC:** Secure registration and session management with hashed passwords (Werkzeug). Strict separation between Administrator and Student roles.
* **Examination Management:** Create, configure, publish, and close examinations with time limits, custom marks, and passing criteria.
* **MCQ Question Management:** Add, edit, and organize multiple-choice questions with 4 options and radio-button answer keys.
* **Live Online Exam Portal:** Real-time countdown timer, question navigation grid, auto-saving of answers, and automatic submission upon timeout.
* **Evaluation Engine:** Automatic calculation of correct, incorrect, unanswered questions, percentage, and pass/fail verdict.
* **Analytics & Reports:** Interactive Chart.js charts for performance tracking, CSV result export, and downloadable official PDF result reports generated using ReportLab.

---

## 🛠️ Technology Stack

* **Backend:** Python 3.11+, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Werkzeug
* **Database:** SQLite (local instance)
* **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5, Bootstrap Icons, Chart.js
* **Reporting & Testing:** ReportLab (PDF generation), pytest

---

## 💻 Local Setup & Execution Instructions

### 1. Prerequisites
* Python 3.11 or newer
* Windows 11 / Linux / macOS
* Git

### 2. Setup Virtual Environment
Open your terminal inside the project folder:

```powershell
cd "Cloud_Examination_System"
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 4. Initialize Database & Seed Sample Data
```powershell
flask init-db
flask seed-data
```

### 5. Run the Application
```powershell
python run.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000/login
```

---

## 🔑 Pre-Configured Accounts

### Administrator Account
* **Email:** `admin@cloudexam.edu` *(or `admin@cloudexam.com`)*
* **Password:** `Admin@12345`

### Student Accounts
* **Email:** `aarav@cloudexam.edu` | **Password:** `Student@12345`
* **Email:** `priya@cloudexam.edu` | **Password:** `Student@12345`
* **Email:** `rohan@cloudexam.edu` | **Password:** `Student@12345`

---

## 🧪 Running Automated Tests

Run the complete test suite using pytest:
```powershell
python -m pytest
```

---

## 📄 License
This project is open-source and available under the MIT License.

