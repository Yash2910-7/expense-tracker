# AI-Powered Flask Expense Tracker

## Description
A comprehensive, full-featured web-based Expense Tracker application built with Flask. This application helps users manage their finances by tracking expenses, setting budgets, and providing AI-driven insights and predictions for future spending. It features secure user authentication and data persistence using JSON files.

## Features
- **User Authentication**: Secure registration and login system with hashed passwords.
- **Expense Management**: Add, edit, delete, and view recurring and one-time expenses.
- **Budget Tracking**: Set a global monthly budget and category-specific limits. Receive warnings when nearing or exceeding limits.
- **Smart Spending Insights**: Automated insights on highest spending categories, most frequent spending days, and month-over-month comparisons, along with budget-tracking projections.
- **AI Expense Prediction**: Uses Machine Learning (Linear Regression) to predict your next month's total expenses based on historical data.
- **Anomaly Detection**: Warns users of unusually high individual expenses to catch unexpected spending.
- **Data Export**: Export your complete expense reports in both standard Text (.txt) and CSV formats.

## Technologies Used
- **Backend Framework**: Python with Flask
- **Data Storage**: JSON (`users.json`, `expenses.json`)
- **Machine Learning & Data Science**: `pandas`, `numpy`, `scikit-learn`
- **Frontend Utilities**: HTML, Jinja2 Templating
- **Security**: Hashlib for password encoding

## Installation & Setup

1. **Prerequisites**: Ensure you have Python 3.x installed on your system.
2. **Navigate to the directory**:
   ```bash
   cd "Expense Tracker"
   ```
3. **Install the required dependencies**:
   Run the following command to install the necessary Python packages using the provided `requirements.txt` file:
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the application**:
   ```bash
   python app.py
   ```
5. **Access the App**: Open your web browser and navigate to `http://127.0.0.1:5000`.

## Project Structure
- `app.py`: The main Flask application containing routing, authentication, and core application logic.
- `templates/`: Contains HTML layout files (`index.html`, `login.html`, `register.html`).
- `users.json`: Database file storing user credentials and budget configurations.
- `expenses.json`: Database file storing expense records categorized by user.
- `requirements.txt`: List of Python dependencies required to run the application.
