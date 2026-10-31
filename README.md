# Olist E-commerce Analytics System

## Project Overview
An admin-focused analytics and management dashboard for Olist, a Brazilian e-commerce company.

The system provides business analytics, data visualization, table management, and user access control.

## Technologies Used
- Python
- FastAPI
- Streamlit
- MySQL
- SQLAlchemy
- Pandas

## Main Features
- Admin login and authentication
- User registration and admin approval
- Role-based access control
- E-commerce analytics dashboard
- Monthly revenue and other business charts
- Database table viewing and searching
- Admin-only record insertion, editing, and deletion
- Reports and CSV export

## Database
The project uses an Olist e-commerce analytics MySQL database.

## Run Locally

### Start the FastAPI backend
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### Start the Streamlit frontend
```bash
python -m streamlit run frontend/frontend/streamlit_app.py
```

## Configuration
Configure database credentials, admin credentials, and authentication secret in a local `.env` file.

Never upload `.env` or database passwords to GitHub.

## Deployment Status
The Streamlit frontend has been deployed. Public login requires the FastAPI backend and MySQL database to be hosted and connected to the deployed frontend.
