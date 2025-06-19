# AgriConnect

AgriConnect is a full-stack web application designed to connect farmers, equipment owners, and agricultural workers. It provides a platform for renting equipment, hiring workers, crop profitability prediction, and more, with multilingual and voice assistant support.

---

## Table of Contents
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Database Setup](#database-setup)
  - [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [Internationalization (i18n)](#internationalization-i18n)
- [Voice Assistant](#voice-assistant)
- [Authentication & Authorization](#authentication--authorization)
- [Admin Features](#admin-features)
- [Email/OTP Setup](#emailotp-setup)
- [Additional Documentation](#additional-documentation)

---

## Features

### User Management
- Registration with email/phone and OTP verification
- Login/logout, profile management, password change
- Role-based access: Farmer, Worker, Renter, Admin

### Equipment Module
- Browse, filter, and search agricultural equipment
- Add, edit, and manage your own equipment
- Book equipment for rent, view bookings
- Equipment reviews and ratings

### Worker Module
- Browse and filter agricultural workers
- Create and manage worker profiles
- Hire workers, manage hirings and requests
- Worker reviews and ratings

### Crop Prediction
- AI-powered crop profitability prediction (Gemini API)
- Input: crop type, area, soil, irrigation, region
- Output: investment, yield, profit, suitability, recommendations

### Bookings
- Manage equipment bookings (as owner and renter)
- Manage worker hiring requests
- Status updates: pending, confirmed, ongoing, completed, cancelled

### Feedback
- Submit feedback, bug reports, and feature requests
- Admin can view and resolve feedback

### Admin Panel
- Dashboard with stats
- Manage users, equipment, workers, feedback
- Approve/reject equipment and worker profiles

### Internationalization (i18n)
- Fully translated UI: English, Hindi, Telugu, Tamil
- Language selector in header

### Voice Assistant
- Voice navigation and commands in multiple languages

---

## Tech Stack
- **Frontend:** React, Material-UI, React Router, i18next
- **Backend:** Flask, Flask-JWT, Flask-CORS, SQLite, Google Gemini API
- **Database:** SQLite (default, can be swapped)
- **Other:** Email (SMTP) for OTP, JWT for auth

---

## Project Structure
```
AgriConnect/
├── backend/           # Flask backend API
│   ├── app.py         # Main Flask app
│   ├── requirements.txt
│   ├── .env.example   # Example environment config
│   ├── ...
├── frontend/          # React frontend
│   ├── src/
│   │   ├── pages/     # Main app pages (equipment, workers, admin, etc.)
│   │   ├── components/
│   │   ├── context/   # React context providers
│   │   ├── i18n/      # Language files
│   │   └── ...
│   ├── package.json
│   └── ...
├── database/          # DB setup scripts, SQLite DB
│   ├── agri_connect.db
│   └── setup.py
├── *.md               # Documentation files
└── README.md
```

---

## Setup & Installation

### Backend Setup
1. **Install Python 3.8+ and pip**
2. Navigate to the backend directory:
   ```bash
   cd backend
   ```
3. (Optional) Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env` and fill in required values (see below).

### Frontend Setup
1. Install Node.js (v16+ recommended) and npm
2. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
3. Install dependencies:
   ```bash
   npm install
   ```

### Database Setup
- The backend uses SQLite by default.
- To initialize the database and tables:
  ```bash
  python database/setup.py
  ```
- The database file will be created at `database/agri_connect.db`.

### Environment Variables
- Copy `backend/.env.example` to `backend/.env` and fill in:
  - `FLASK_APP`, `FLASK_ENV`, `SECRET_KEY`, `JWT_SECRET_KEY`, `GEMINI_API_KEY`, `EMAIL_ID`, `EMAIL_PASSWORD`
- For email/OTP, see [Email/OTP Setup](#emailotp-setup).

---

## Running the Application

### Start Backend (Flask API)
```bash
cd backend
flask run
```
- The API will be available at `http://localhost:5000`

### Start Frontend (React)
```bash
cd frontend
npm start
```
- The app will be available at `http://localhost:3000`

---

## Internationalization (i18n)
- Supported languages: English, Hindi, Telugu, Tamil
- Change language using the selector in the header
- All major pages and features are translated

## Voice Assistant
- Use the microphone button in the header to activate
- Supports navigation and actions in multiple languages

## Authentication & Authorization
- Registration with email/phone and OTP verification
- Login/logout, JWT-based session management
- Role-based access: Farmer, Worker, Renter, Admin
- Protected routes for sensitive pages

## Admin Features
- Admin dashboard with stats
- Manage users, equipment, workers, feedback
- Approve/reject equipment and worker profiles
- View and resolve feedback

## Email/OTP Setup
- For email verification, configure Gmail as described in `EMAIL_SETUP_INSTRUCTIONS.md` and `GMAIL_SETUP_GUIDE.md`
- Set `EMAIL_ID` and `EMAIL_PASSWORD` in `backend/.env` (use an App Password for Gmail)

---

## Additional Documentation
- [EQUIPMENT_GUIDE.md](EQUIPMENT_GUIDE.md): Equipment management
- [AUTHENTICATION_FLOW.md](AUTHENTICATION_FLOW.md): Auth flow and route protection
- [LANGUAGE_IMPLEMENTATION.md](LANGUAGE_IMPLEMENTATION.md): i18n details
- [IMPLEMENTED_FEATURES.md](IMPLEMENTED_FEATURES.md): Full feature list
- [EMAIL_SETUP_INSTRUCTIONS.md](EMAIL_SETUP_INSTRUCTIONS.md): Email/OTP setup
- [GMAIL_SETUP_GUIDE.md](GMAIL_SETUP_GUIDE.md): Gmail App Password setup

# 👥 Contributors

We extend our heartfelt thanks to the individuals who have contributed their time, skills, and effort to make **AgriConnect** a reality.

## Core Team

-  **Shanmukha** 
-  **Prudvi venkat** 
-  **Surya Prakash Reddy** 

> **Note:** This project is for educational and demonstration purposes only.

---

## License
This project is for educational and demonstration purposes. 
