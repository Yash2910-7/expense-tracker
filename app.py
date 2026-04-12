# Import necessary modules
# flask for web serving, session for user sessions, flash for messages
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
# json for file storage
import json
# os for checking file existence
import os
# datetime for dates
from datetime import datetime
# hashlib for hashing user passwords securely
import hashlib
# uuid for generating unique expense IDs
import uuid
# smtplib for sending email reports
import smtplib
from email.mime.text import MIMEText
from collections import Counter
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# Initialize the Flask application
app = Flask(__name__)
# Secret key is required to use Flask sessions securely
app.secret_key = "super_secret_expense_tracker_key_for_beginners"

# Constants for file paths and limits
USERS_FILE = "users.json"
EXPENSES_FILE = "expenses.json"
# The required budget limit per month
DEFAULT_BUDGET = 5000

# ==========================================
# Helper Functions for File I/O
# ==========================================

# Function to read JSON data from a file
def load_json(filepath):
    # Check if file exists, if not, return an empty dictionary
    if not os.path.exists(filepath):
        return {}
    # Try to open and load the JSON
    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except json.JSONDecodeError:
        # If file is corrupted or empty, return an empty dictionary
        return {}

# Function to write JSON data to a file
def save_json(filepath, data):
    # Open the file in write mode and dump the python dictionary to JSON
    with open(filepath, 'w') as file:
        json.dump(data, file, indent=4)

# Function to convert a plain text password into a secure hash
def hash_password(password):
    # Create a SHA-256 hash object, encode the string, and return hex digest
    return hashlib.sha256(password.encode()).hexdigest()

# Function to predict next month's expense using Machine Learning
def predict_next_month_expense(user_expenses):
    # If user has less than 2 data points, prediction is unreliable
    if len(user_expenses) < 2:
        return "Need more data"

    # Aggregate data by month
    monthly_totals = {}
    for exp in user_expenses:
        month = exp["date"][:7] # YYYY-MM
        monthly_totals[month] = monthly_totals.get(month, 0) + float(exp["amount"])
    
    # Sort chronologically
    sorted_months = sorted(monthly_totals.keys())
    
    # Create DataFrame mapping
    df = pd.DataFrame({
        "Month": sorted_months,
        "Total": [monthly_totals[m] for m in sorted_months]
    })
    
    # Needs chronological sequence (0, 1, 2)
    df['TimeIndex'] = np.arange(len(df))
    
    # Train Linear Regression model
    X = df[['TimeIndex']]
    y = df['Total']
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict next chronological interval
    next_time_index = np.array([[len(df)]])
    prediction = model.predict(next_time_index)[0]
    
    return max(0, round(prediction, 2))

# ==========================================
# Authentication Routes
# ==========================================

# Route to display and handle user registration
@app.route("/register", methods=["GET", "POST"])
def register():
    # If using POST, the form has been submitted
    if request.method == "POST":
        # Get data from the form
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        
        # Load existing users
        users = load_json(USERS_FILE)
        
        # Check if the username is already taken
        if username in users:
            flash("Username already exists. Please choose another.", "error")
            return redirect(url_for("register"))
        
        # Save the new user with a hashed password
        users[username] = {
            "email": email,
            "password_hash": hash_password(password),
            "global_budget": DEFAULT_BUDGET,
            "category_budgets": {
                "Food": 2000,
                "Travel": 1000,
                "Shopping": 1500,
                "Bills": 3000,
                "Entertainment": 1000,
                "Other": 500
            }
        }
        # Save data back to the file
        save_json(USERS_FILE, users)
        
        flash("Registration successful! You may now login.", "success")
        # Redirect the user to the login screen
        return redirect(url_for("login"))
        
    # If GET request, just display the registration page
    return render_template("register.html")

# Route to display and handle user login
@app.route("/login", methods=["GET", "POST"])
def login():
    # If form is submitted via POST
    if request.method == "POST":
        # Get form data
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Load existing users
        users = load_json(USERS_FILE)
        
        # Check if user exists and password hash matches
        if username in users and users[username]["password_hash"] == hash_password(password):
            # Login successful: store the username in the session cookie
            session["username"] = username
            # Redirect to the main dashboard
            return redirect(url_for("index"))
        else:
            # Failure message
            flash("Invalid username or password.", "error")
    
    # Check if user is already logged in
    if "username" in session:
        return redirect(url_for("index"))
        
    # Render the login template
    return render_template("login.html")

# Route to logout the user
@app.route("/logout")
def logout():
    # Remove the username from the session memory
    session.pop("username", None)
    # Send user back to the login page
    return redirect(url_for("login"))

# ==========================================
# Application Routes
# ==========================================

# Main Dashboard route
@app.route("/")
def index():
    # Protect route: Ensure the user is logged in
    if "username" not in session:
        # Redirect to login if user isn't authenticated
        return redirect(url_for("login"))
    
    # Grab the logged-in username
    user = session["username"]
    # Load all global expenses
    all_expenses = load_json(EXPENSES_FILE)
    
    # Extract only this user's expenses (defaulting to empty list if none exist)
    user_expenses = all_expenses.get(user, [])
    
    # Calculate Total Spending
    total_spent = sum(float(exp["amount"]) for exp in user_expenses)
    
    # Dictionary to track spending per category
    category_summary = {}
    for exp in user_expenses:
        cat = exp["category"]
        category_summary[cat] = category_summary.get(cat, 0) + float(exp["amount"])
        
    # Dictionary to track spending per month (YYYY-MM)
    monthly_summary = {}
    for exp in user_expenses:
        # Assumes date format is YYYY-MM-DD, grab the first 7 characters
        month = exp["date"][:7]
        monthly_summary[month] = monthly_summary.get(month, 0) + float(exp["amount"])

    # Number of expenses constraint calculation
    total_count = len(user_expenses)
    
    # Feature 1: Category Budget System Warnings
    user_data = load_json(USERS_FILE).get(user, {})
    category_budgets = user_data.get("category_budgets", {})
    
    # Map the localized budget dynamically
    user_budget = float(user_data.get("global_budget", DEFAULT_BUDGET))
    
    # Remaining budget logic
    remaining_budget = user_budget - total_spent
    # Check if user exceeded standard budget
    over_budget = total_spent > user_budget
    
    category_warnings = []
    for cat, spent in category_summary.items():
        limit = category_budgets.get(cat, 0)
        if limit > 0 and spent > limit:
            category_warnings.append(f"⚠️ You exceeded the {cat} budget by ₹{spent - limit}!")
            
    # Feature 5: New Smart Spending Insights
    insights = []
    
    # Insight 1: Highest spending category
    if total_spent > 0 and category_summary:
        highest_category = max(category_summary, key=category_summary.get)
        max_amount = category_summary[highest_category]
        percent_drain = int((max_amount / total_spent) * 100)
        insights.append(f"Your highest spending category is {highest_category} ({percent_drain}%)")
        
    # Insight 2: Most frequent spending day
    try:
        if user_expenses:
            days_of_week = [datetime.strptime(exp['date'], "%Y-%m-%d").strftime('%A')+'s' for exp in user_expenses]
            if days_of_week:
                frequent_day_str = Counter(days_of_week).most_common(1)[0][0]
                insights.append(f"You spend most on {frequent_day_str}")
    except Exception:
        pass

    # Insight 3: Spending compared to last month
    if len(monthly_summary) >= 2:
        sorted_months = sorted(monthly_summary.keys())
        last_month = sorted_months[-2]
        this_month = sorted_months[-1]
        last_month_spend = monthly_summary[last_month]
        this_month_spend = monthly_summary[this_month]
        if last_month_spend > 0:
            diff = ((this_month_spend - last_month_spend) / last_month_spend) * 100
            trend = "increased" if diff > 0 else "decreased"
            insights.append(f"Your spending {trend} {abs(int(diff))}% compared to last month")

    # Insight 4: On track to exceed budget
    current_day = datetime.now().day
    days_in_month = 30 # Simple estimation
    if current_day > 0 and user_budget > 0:
        # Calculate spending only for the current month to be accurate
        current_month = datetime.now().strftime("%Y-%m")
        current_month_spend = monthly_summary.get(current_month, 0)
        daily_average = current_month_spend / current_day
        projected_spend = daily_average * days_in_month
        if projected_spend > user_budget:
            exceed_amount = int(projected_spend - user_budget)
            insights.append(f"You are on track to exceed budget by ₹{exceed_amount} this month")

    # Calculate daily spending trend for line chart (current month)
    current_month_prefix = datetime.now().strftime("%Y-%m")
    daily_summary = {}
    for exp in user_expenses:
        if exp["date"].startswith(current_month_prefix):
            day = exp["date"][-2:] # Extract day string e.g., '14'
            daily_summary[day] = daily_summary.get(day, 0) + float(exp["amount"])

    # Calculate AI prediction
    predicted_expense = predict_next_month_expense(user_expenses)

    # Render dashboard passing all required variables for UI and Javascript Charts
    return render_template("index.html",
                           username=user,
                           expenses=user_expenses,
                           total_spent=total_spent,
                           remaining_budget=remaining_budget,
                           budget=user_budget,
                           over_budget=over_budget,
                           total_count=total_count,
                           category_summary=category_summary,
                           monthly_summary=monthly_summary,
                           predicted_expense=predicted_expense,
                           category_warnings=category_warnings,
                           insights=insights,
                           daily_summary=daily_summary,
                           category_budgets=category_budgets)

# Route to update the global monthly budget dynamically
@app.route("/update_budget", methods=["POST"])
def update_budget():
    if "username" not in session:
        return redirect(url_for("login"))
        
    user = session["username"]
    new_budget = request.form.get("new_budget")
    
    if new_budget:
        users = load_json(USERS_FILE)
        if user in users:
            users[user]["global_budget"] = float(new_budget)
            save_json(USERS_FILE, users)
            flash(f"Monthly budget explicitly updated to ₹{new_budget}!", "success")
            
    return redirect(url_for("index"))

# Route to add a new expense form processing
@app.route("/add", methods=["POST"])
def add_expense():
    # Protection check
    if "username" not in session:
        return redirect(url_for("login"))
        
    # Grab form variables
    name = request.form.get("name")
    amount = request.form.get("amount")
    category = request.form.get("category")
    date = request.form.get("date")
    notes = request.form.get("notes", "") # Optional field
    # Checkbox sends "on" if clicked, else None
    recurring = True if request.form.get("recurring") == "on" else False
    
    # Create a globally unique identifier for this specific expense
    expense_id = str(uuid.uuid4())
    
    # The new expense dictionary object
    new_expense = {
        "id": expense_id,
        "name": name,
        "amount": amount,
        "category": category,
        "date": date,
        "notes": notes,
        "recurring": recurring
    }
    
    # Insert new expense into the user's list
    all_expenses = load_json(EXPENSES_FILE)
    user = session["username"]
    
    if user not in all_expenses:
        # If user has no record yet, create an empty list
        all_expenses[user] = []
        
    # Anomaly Detection Feature
    user_exps = all_expenses[user]
    if len(user_exps) > 3:
        historical_amounts = [float(e["amount"]) for e in user_exps]
        avg_expense = np.mean(historical_amounts)
        if float(amount) > (avg_expense * 2.5):
            flash(f"Unusual spending detected! ₹{amount} is significantly higher than your typical average of ₹{round(avg_expense)}.", "warning")

    # Append element
    all_expenses[user].append(new_expense)
    # Save back to file permanently
    save_json(EXPENSES_FILE, all_expenses)
    
    flash("Expense added successfully!", "success")
    return redirect(url_for("index"))

# Route to delete a single expense by ID
@app.route("/delete/<id>")
def delete_expense(id):
    if "username" not in session:
        return redirect(url_for("login"))
        
    all_expenses = load_json(EXPENSES_FILE)
    user = session["username"]
    
    # Perform deletion by filtering out the matching ID
    if user in all_expenses:
        # Keep items where id doesn't match the passed id
        all_expenses[user] = [exp for exp in all_expenses[user] if exp["id"] != id]
        save_json(EXPENSES_FILE, all_expenses)
        flash("Expense deleted.", "success")
        
    return redirect(url_for("index"))

# Route to edit an existing expense
@app.route("/edit/<id>", methods=["POST"])
def edit_expense(id):
    if "username" not in session:
        return redirect(url_for("login"))
        
    user = session["username"]
    all_expenses = load_json(EXPENSES_FILE)
    
    if user in all_expenses:
        # Find the specific expense
        for exp in all_expenses[user]:
            # if matching id found
            if exp["id"] == id:
                # Update properties using form values
                exp["name"] = request.form.get("name")
                exp["amount"] = request.form.get("amount")
                exp["category"] = request.form.get("category")
                exp["date"] = request.form.get("date")
                exp["notes"] = request.form.get("notes", "")
                exp["recurring"] = True if request.form.get("recurring") == "on" else False
                break # Exit the loop after finding it
                
        # Save updated data
        save_json(EXPENSES_FILE, all_expenses)
        flash("Expense modified.", "success")
        
    return redirect(url_for("index"))

# Route to export data formatted as a text file
@app.route("/export")
def export_data():
    if "username" not in session:
        return redirect(url_for("login"))
        
    user = session["username"]
    all_expenses = load_json(EXPENSES_FILE)
    user_expenses = all_expenses.get(user, [])
    
    filename = f"{user}_expense_report.txt"
    
    # Write report details into a file
    with open(filename, "w") as file:
        file.write(f"--- EXPENSE REPORT FOR {user.upper()} ---\n\n")
        total = 0
        for exp in user_expenses:
            rec_str = "(Recurring)" if exp["recurring"] else ""
            file.write(f"Date: {exp['date']} | Name: {exp['name']} {rec_str}\n")
            file.write(f"Category: {exp['category']} | Amount: Rs. {exp['amount']} | Notes: {exp['notes']}\n")
            file.write("-" * 40 + "\n")
            total += float(exp["amount"])
            
        file.write(f"\nTOTAL SPENT: Rs. {total}\n")
        
    # Transmit file to client as an attachment prompt
    return send_file(filename, as_attachment=True)

# Route to export data formatted as a CSV file
@app.route("/export_csv")
def export_csv_data():
    if "username" not in session:
        return redirect(url_for("login"))
        
    user = session["username"]
    all_expenses = load_json(EXPENSES_FILE)
    user_expenses = all_expenses.get(user, [])
    
    import csv, io
    from flask import Response
    
    # Create a string buffer to write CSV data
    si = io.StringIO()
    cw = csv.writer(si)
    
    # Write header row for the CSV file
    cw.writerow(['Date', 'Name', 'Category', 'Amount', 'Notes'])
    
    # Write each expense as a row in the CSV file
    for exp in user_expenses:
        cw.writerow([exp.get('date', ''), exp.get('name', ''), exp.get('category', ''), exp.get('amount', ''), exp.get('notes', '')])
        
    # Get the CSV string
    output = si.getvalue()
    
    # Return as a downloadable csv file using Flask Response
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={user}_expenses.csv"}
    )

# Experimental route to mock sending an email (as requested)
@app.route("/email_report")
def email_report():
    if "username" not in session:
        return redirect(url_for("login"))
        
    # Since we shouldn't hardcode real plaintext passwords, we mock the success.
    # In a real environment, you would use:
    # server = smtplib.SMTP('smtp.gmail.com', 587)
    # server.starttls()
    # server.login('your_email@gmail.com', 'your_app_password')
    # server.sendmail(...)
    
    flash("Email report successfully generated and simulated sending!", "success")
    # Redirecting safely back to dashboard
    return redirect(url_for("index"))

# Main entrypoint
if __name__ == "__main__":
    # Start the Flask web app automatically mapping onto port 5000 in debug mode
    app.run(debug=True)
