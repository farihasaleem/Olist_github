# Olist Brazilian E-commerce Analytics & Management System

## 1. Project Overview

The Olist E-commerce Analytics & Management System is a database-driven application developed to analyze and manage Brazilian e-commerce business data.

The project focuses on transforming raw e-commerce data into meaningful business insights through MySQL queries, data analysis, and an interactive dashboard.

The system provides analytics related to orders, customers, sellers, products, payments, reviews, and revenue.

## 2. Domain Focus

**Domain:** E-commerce Analytics and Business Intelligence

**Company:** Olist (Brazilian e-commerce marketplace)

The project focuses on:
- Sales and revenue analysis
- Customer purchasing behavior
- Product and category performance
- Seller performance
- Order and delivery analysis
- Payment methods
- Customer reviews and satisfaction

## 3. Technologies Used

| Technology | Purpose |
|---|---|
| MySQL | Database management and SQL queries |
| Jupyter Notebook | Data exploration and analysis |
| Python | Application development |
| FastAPI | Backend and API development |
| Streamlit | Interactive dashboard |
| Pandas | Data processing |
| SQLAlchemy | Database connectivity |

## 4. Database Structure

The project uses an existing MySQL database named `E_commerce_analytics`.

The main tables include:

1. customers
2. sellers
3. products
4. category_translation
5. orders
6. order_items
7. order_payments
8. order_reviews

The database supports relational queries and business analytics across different aspects of the Olist marketplace.

## 5. SQL & Jupyter Notebook Work

SQL and database analysis were performed during the project using Jupyter Notebook and MySQL.

This work includes:
- Database exploration and table inspection
- Retrieving records using SELECT queries
- Filtering and sorting data
- Joining related tables
- Aggregate functions such as SUM, COUNT, and AVG
- Grouping data for business analysis
- Revenue and order analysis
- Exploring customer reviews and delivery performance

**Notebook:** The Jupyter Notebook containing the project's database and analytical work is included in this repository.

## 6. Prompt Engineering

AI-assisted prompting was used during the planning and development of the application.

### Main Project Development Prompt

"Develop an e-commerce analytics and management system for Olist, a Brazilian e-commerce company. Use the existing MySQL database and its tables and data. Build a Python FastAPI backend connected to MySQL and a Streamlit frontend. Include business analytics, interactive charts, database table viewing, searching, and record management. Implement administrator authentication, user registration, approval, and role-based permissions. Inspect the existing database structure before developing the application and preserve the existing data."

### Prompting Approach

The project was developed through iterative prompting:

1. Defining the project requirements and technology stack.
2. Understanding the existing database structure.
3. Generating backend APIs and database connectivity.
4. Developing dashboard layouts and analytical visualizations.
5. Implementing authentication and user permissions.
6. Refining the interface and troubleshooting errors.

Prompts were refined as the application developed to improve functionality, design, and accuracy.

## 7. Dashboard Features

The Streamlit dashboard provides:
<img width="1912" height="924" alt="image" src="https://github.com/user-attachments/assets/05d8e1e9-3c04-4a0c-82a5-310d20ed5272" />

- Monthly revenue analysis
- Order and sales analytics
- Customer and product insights
- Payment method analysis
- Review versus delivery analysis
- Database table navigation
- Record insertion, updating, and deletion for administrators
<img width="1402" height="799" alt="image" src="https://github.com/user-attachments/assets/8bbf690f-7f97-4b29-8b2f-60e62a4fa645" />

- Reports and data export
<img width="1403" height="452" alt="image" src="https://github.com/user-attachments/assets/0506fc98-b318-4316-a6eb-79cd1cc13a89" />

- Admin Settings 
<img width="1420" height="721" alt="image" src="https://github.com/user-attachments/assets/d4beb823-69b6-4dbf-9099-5bbe6a1d4915" />

## 8. System Architecture

The application follows a three-layer architecture:

**Database Layer:** MySQL stores the Olist e-commerce data.

**Backend Layer:** FastAPI provides APIs, database operations, authentication, and access control.

**Frontend Layer:** Streamlit provides the interactive dashboard and user interface.

Architecture:

MySQL → FastAPI → Streamlit

## 9. Authentication & Access Control

The system includes:
- Administrator login
- User registration
- Admin approval for new accounts
- Administrator-only database modifications
- Read-only access for approved users
<img width="1910" height="918" alt="image" src="https://github.com/user-attachments/assets/61a626a3-6b95-4785-89c1-71f7a7b23325" />

## 10. Project Objectives

- Analyze Brazilian e-commerce business data.
- Apply SQL for database querying and analysis.
- Develop an interactive business intelligence dashboard.
- Connect a relational database with a Python backend.
- Implement secure, role-based application access.
- Present business information in an understandable format.

## 11. How to Run the Dashboard Locally

Follow these steps to run the project on your computer.

### Prerequisites
- Python installed
- MySQL Server installed
- MySQL database configured with the Olist dataset
- Project repository downloaded

### Step 1: Clone the Repository

```bash
git clone https://github.com/farihasaleem/Olist_github.git
cd Olist_github
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create a `.env` file in the project root directory and configure your own database credentials and authentication settings.

Do not upload your `.env` file to GitHub.

### Step 4: Initialize Authentication

```bash
python -c "from app.init_auth import initialize_auth; initialize_auth(); print('Admin account initialized!')"
```

### Step 5: Start the FastAPI Backend

Open a terminal and run:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Backend API documentation:

http://127.0.0.1:8001/docs

### Step 6: Start the Streamlit Dashboard

Open a second terminal and run:

```bash
python -m streamlit run frontend/frontend/streamlit_app.py
```

### Step 7: Open the Dashboard

Open your browser and visit:

http://localhost:8501

Log in using the administrator credentials configured during setup.

**Note:** The dashboard runs locally. Each user must configure their own MySQL database and environment variables before running the application.

## 12. Future Improvements

- Automated data updates
- Additional business intelligence metrics
- Advanced predictive analytics
- Improved deployment and cloud database integration
- More detailed reporting features

## 13. Conclusion

This project demonstrates the integration of relational database management, SQL-based analysis, Python application development, API development, and interactive data visualization in a practical e-commerce business environment.

