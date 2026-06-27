from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, send_from_directory
from models import db
from models.expense import Expense
from routes.auth import token_required
from services.receipt_service import save_receipt, delete_receipt, serve_receipt_file
from ml.anomaly_detector import detect_anomaly

expenses_bp = Blueprint('expenses', __name__)

def get_currency_rate(currency_code):
    rates = {'INR': 1.0, 'USD': 83.0, 'EUR': 90.0, 'GBP': 105.0}
    return rates.get(currency_code, 1.0)

@expenses_bp.route('/expenses', methods=['GET'])
@token_required
def index():
    user = g.current_user
    rate = get_currency_rate(user.currency)
    
    # Query parameters
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', 'All')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    min_amount = request.args.get('min_amount', '')
    max_amount = request.args.get('max_amount', '')
    sort_by = request.args.get('sort_by', 'date-desc')
    
    # Build filter query
    query = Expense.query.filter_by(user_id=user.id)
    
    if search_query:
        query = query.filter(Expense.description.ilike(f"%{search_query}%"))
        
    if category_filter != 'All':
        query = query.filter(Expense.category == category_filter)
        
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Expense.date >= start_dt)
        except ValueError:
            pass
            
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Expense.date <= end_dt)
        except ValueError:
            pass
            
    if min_amount:
        try:
            # We filter by raw database amounts. Let's convert if needed, or filter straight
            # We assume user inputs amount in their selected currency, so multiply by rate to match database (INR base)
            query = query.filter(Expense.amount >= float(min_amount) * rate)
        except ValueError:
            pass
            
    if max_amount:
        try:
            query = query.filter(Expense.amount <= float(max_amount) * rate)
        except ValueError:
            pass
            
    # Sorting
    if sort_by == 'date-asc':
        query = query.order_by(Expense.date.asc())
    elif sort_by == 'amount-asc':
        query = query.order_by(Expense.amount.asc())
    elif sort_by == 'amount-desc':
        query = query.order_by(Expense.amount.desc())
    else: # date-desc
        query = query.order_by(Expense.date.desc())
        
    expenses = query.all()
    
    # Convert amounts for display
    converted_expenses = []
    for exp in expenses:
        exp_dict = exp.to_dict()
        exp_dict['amount'] = exp.amount / rate
        converted_expenses.append(exp_dict)
        
    # Categories list for the selector
    categories = [
        "🍔 Food", "✈️ Travel", "🛒 Shopping", "💡 Bills", "🎮 Entertainment",
        "🏥 Health", "📚 Education", "🏠 Rent", "🚗 Transport", "📱 Subscription"
    ]
    
    # Currency details
    symbol = '₹'
    if user.currency == 'USD': symbol = '$'
    elif user.currency == 'EUR': symbol = '€'
    elif user.currency == 'GBP': symbol = '£'
    
    return render_template('expenses.html',
                           user=user,
                           expenses=converted_expenses,
                           categories=categories,
                           currency_symbol=symbol,
                           search=search_query,
                           category_filter=category_filter,
                           start_date=start_date,
                           end_date=end_date,
                           min_amount=min_amount,
                           max_amount=max_amount,
                           sort_by=sort_by)

@expenses_bp.route('/expenses/add', methods=['POST'])
@token_required
def add():
    user = g.current_user
    rate = get_currency_rate(user.currency)
    
    amount = request.form.get('amount')
    category = request.form.get('category')
    date_str = request.form.get('date')
    description = request.form.get('description', '').strip()
    receipt_file = request.files.get('receipt')
    
    if not amount or not category or not date_str:
        flash("Required fields are missing.", "danger")
        return redirect(url_for('expenses.index'))
        
    try:
        # Convert user amount input to base rate (INR)
        amount_val = float(amount) * rate
        date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid amount or date format.", "danger")
        return redirect(url_for('expenses.index'))
        
    # Check Anomaly BEFORE inserting, by querying historical user expenses
    historical_expenses = Expense.query.filter_by(user_id=user.id).all()
    is_anomalous = detect_anomaly(amount_val, historical_expenses)
    
    if is_anomalous:
        symbol = '₹'
        if user.currency == 'USD': symbol = '$'
        elif user.currency == 'EUR': symbol = '€'
        elif user.currency == 'GBP': symbol = '£'
        flash(f"⚠️ Unusual Expense Detected! The amount {symbol}{float(amount):,.2f} is significantly higher than your typical average in this category.", "warning")
        
    # Save receipt if present
    receipt_filename = None
    if receipt_file:
        receipt_filename = save_receipt(receipt_file)
        
    # Create Expense
    new_expense = Expense(
        user_id=user.id,
        category=category,
        amount=amount_val,
        description=description,
        date=date_val,
        receipt_filename=receipt_filename
    )
    
    try:
        db.session.add(new_expense)
        db.session.commit()
        flash("Expense added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        if receipt_filename:
            delete_receipt(receipt_filename)
        flash(f"Failed to save transaction: {str(e)}", "danger")
        
    return redirect(url_for('expenses.index'))

@expenses_bp.route('/expenses/edit/<int:id>', methods=['POST'])
@token_required
def edit(id):
    user = g.current_user
    rate = get_currency_rate(user.currency)
    expense = Expense.query.filter_by(id=id, user_id=user.id).first_or_404()
    
    amount = request.form.get('amount')
    category = request.form.get('category')
    date_str = request.form.get('date')
    description = request.form.get('description', '').strip()
    receipt_file = request.files.get('receipt')
    
    if not amount or not category or not date_str:
        flash("Required fields are missing.", "danger")
        return redirect(url_for('expenses.index'))
        
    try:
        amount_val = float(amount) * rate
        date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid amount or date.", "danger")
        return redirect(url_for('expenses.index'))
        
    expense.amount = amount_val
    expense.category = category
    expense.date = date_val
    expense.description = description
    
    # Handle new receipt upload (and delete old one)
    if receipt_file and receipt_file.filename != '':
        if expense.receipt_filename:
            delete_receipt(expense.receipt_filename)
        expense.receipt_filename = save_receipt(receipt_file)
        
    try:
        db.session.commit()
        flash("Expense entry updated.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update expense: {str(e)}", "danger")
        
    return redirect(url_for('expenses.index'))

@expenses_bp.route('/expenses/delete/<int:id>', methods=['POST'])
@token_required
def delete(id):
    user = g.current_user
    expense = Expense.query.filter_by(id=id, user_id=user.id).first_or_404()
    
    # Delete uploaded receipt file
    if expense.receipt_filename:
        delete_receipt(expense.receipt_filename)
        
    try:
        db.session.delete(expense)
        db.session.commit()
        flash("Expense entry deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Deletion failed: {str(e)}", "danger")
        
    return redirect(url_for('expenses.index'))

@expenses_bp.route('/expenses/receipt/<filename>')
@token_required
def view_receipt(filename):
    return serve_receipt_file(filename)
