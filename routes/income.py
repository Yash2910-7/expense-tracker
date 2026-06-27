from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models import db
from models.income import Income
from routes.auth import token_required

income_bp = Blueprint('income', __name__)

def get_currency_rate(currency_code):
    rates = {'INR': 1.0, 'USD': 83.0, 'EUR': 90.0, 'GBP': 105.0}
    return rates.get(currency_code, 1.0)

@income_bp.route('/income', methods=['GET'])
@token_required
def index():
    user = g.current_user
    rate = get_currency_rate(user.currency)
    
    # Fetch user incomes
    incomes = Income.query.filter_by(user_id=user.id).order_by(Income.date.desc()).all()
    
    # Convert amounts for display
    converted_incomes = []
    for inc in incomes:
        inc_dict = inc.to_dict()
        inc_dict['amount'] = inc.amount / rate
        converted_incomes.append(inc_dict)
        
    # Sources list
    sources = ["Salary", "Freelancing", "Business", "Investment", "Other"]
    
    # Currency symbol
    symbol = '₹'
    if user.currency == 'USD': symbol = '$'
    elif user.currency == 'EUR': symbol = '€'
    elif user.currency == 'GBP': symbol = '£'
    
    # Monthly Income Analytics
    monthly_analytics = {}
    for inc in incomes:
        month = inc.date.strftime("%Y-%m")
        monthly_analytics[month] = monthly_analytics.get(month, 0.0) + (inc.amount / rate)
        
    # Sort monthly analytics by keys
    sorted_analytics = dict(sorted(monthly_analytics.items(), reverse=True))
    
    return render_template('income.html',
                           user=user,
                           incomes=converted_incomes,
                           sources=sources,
                           currency_symbol=symbol,
                           monthly_analytics=sorted_analytics)

@income_bp.route('/income/add', methods=['POST'])
@token_required
def add():
    user = g.current_user
    rate = get_currency_rate(user.currency)
    
    amount = request.form.get('amount')
    source = request.form.get('source')
    date_str = request.form.get('date')
    description = request.form.get('description', '').strip()
    
    if not amount or not source or not date_str:
        flash("Required fields are missing.", "danger")
        return redirect(url_for('income.index'))
        
    try:
        amount_val = float(amount) * rate
        date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid amount or date.", "danger")
        return redirect(url_for('income.index'))
        
    new_income = Income(
        user_id=user.id,
        source=source,
        amount=amount_val,
        date=date_val,
        description=description
    )
    
    try:
        db.session.add(new_income)
        db.session.commit()
        flash("Income record added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to add income record: {str(e)}", "danger")
        
    return redirect(url_for('income.index'))

@income_bp.route('/income/edit/<int:id>', methods=['POST'])
@token_required
def edit(id):
    user = g.current_user
    rate = get_currency_rate(user.currency)
    income = Income.query.filter_by(id=id, user_id=user.id).first_or_404()
    
    amount = request.form.get('amount')
    source = request.form.get('source')
    date_str = request.form.get('date')
    description = request.form.get('description', '').strip()
    
    if not amount or not source or not date_str:
        flash("Required fields are missing.", "danger")
        return redirect(url_for('income.index'))
        
    try:
        amount_val = float(amount) * rate
        date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid amount or date.", "danger")
        return redirect(url_for('income.index'))
        
    income.amount = amount_val
    income.source = source
    income.date = date_val
    income.description = description
    
    try:
        db.session.commit()
        flash("Income record modified.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update income record: {str(e)}", "danger")
        
    return redirect(url_for('income.index'))

@income_bp.route('/income/delete/<int:id>', methods=['POST'])
@token_required
def delete(id):
    user = g.current_user
    income = Income.query.filter_by(id=id, user_id=user.id).first_or_404()
    
    try:
        db.session.delete(income)
        db.session.commit()
        flash("Income record deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Deletion failed: {str(e)}", "danger")
        
    return redirect(url_for('income.index'))
