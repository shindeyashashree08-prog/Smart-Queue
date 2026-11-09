# SmartQueue – A Smart Digital Queue Management System

**College Mini Project**  
- **Student Name:** Yashashri Shekhar Shinde  
- **PRN Number:** 24062171263077  
- **Roll Number:** 437  
- **Admission Year:** 2024–2025  
- **Department:** Artificial Intelligence and Data Science (AI&DS)  
- **Project Guide & Coordinator:** S. R. Pol Mam  

---

## 1. Project Overview
SmartQueue is a web-based digital queue management system designed to eliminate physical waiting lines in hospitals, banks, college offices, salons, and government service centers. Users can register, take a digital queue token from any device, track real-time queue position, and arrive right on time. Administrators have a dedicated counter control panel to call the next customer, mark completed, or skip absent tokens.

---

## 2. Technology Stack
- **Frontend:** HTML5, CSS3, Vanilla JavaScript (No heavy frameworks, fast & responsive)
- **Backend:** Python 3 with Flask Web Framework
- **Database:** SQLite3 (`smartqueue.db`)
- **Security:** SHA-256 password hashing, secure session management

---

## 3. Project Folder Structure
```text
smartqueue/
│
├── database.py              # SQLite database schema, tables & seed data
├── app.py                   # Main Flask application & route controllers
├── requirements.txt         # Project dependencies (Flask)
├── README.md                # Project documentation and guide
│
├── static/
│   ├── css/
│   │   └── style.css        # Professional, responsive modern styling
│   └── js/
│       └── main.js          # Live queue polling and interactive confirmations
│
└── templates/
    ├── base.html            # Main template layout with navbar & academic footer
    ├── index.html           # Landing homepage with services and stats
    ├── register.html        # User registration form
    ├── login.html           # User login form
    ├── dashboard.html       # User dashboard with live token position & wait time
    ├── admin_login.html     # Administrator authentication portal
    └── admin_dashboard.html # Counter operator management console
```

---

## 4. How to Run the Project

### Step 1: Open Terminal in VS Code
Open the `smartqueue` folder in VS Code. Open terminal (`Ctrl + ~`).

### Step 2: Install Flask
```bash
pip install -r requirements.txt
```
*(or `pip install flask`)*

### Step 3: Initialize Database
```bash
python database.py
```
This creates `smartqueue.db` with the default tables, 5 initial services, and the admin account.

### Step 4: Start the Application
```bash
python app.py
```

### Step 5: Open in Browser
- **User Portal:** `http://127.0.0.1:5000`
- **Admin Portal:** `http://127.0.0.1:5000/admin/login`
  - **Username:** `admin`
  - **Password:** `admin123`
