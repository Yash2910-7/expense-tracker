from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models import db
from models.savings import SavingsGoal
from models.expense import Expense
from models.income import Income
from routes.auth import token_required

savings_bp = Blueprint('savings', __name__)

def get_currency_rate(currency_code):
    rates = {'INR': 1.0, 'USD': 83.0, 'EUR': 90.0, 'GBP': 105.0}
    return rates.get(currency_code, 1.0)

@savings_bp.route('/savings', methods=['GET'])
@token_required
def index():
    user = g.current_user
    rate = get_currency_rate(user.currency)
    
    # Load goals
    goals = SavingsGoal.query.filter_by(user_id=user.id).order_by(SavingsGoal.deadline.asc()).all()
    
    # User transactions to compute monthly savings rate
    expenses = Expense.query.filter_by(user_id=user.id).all()
    incomes = Income.query.filter_by(user_id=user.id).all()
    
    total_exp = sum(e.amount for e in expenses)
    total_inc = sum(i.amount for i in incomes)
    
    # Calculate months active (at least 1 to avoid ZeroDivisionError)
    min_date = date.today()
    if expenses or incomes:
        all_dates = [e.date for e in expenses] + [i.date for i in incomes]
        min_date = min(all_dates)
    
    days_active = max(1, (date.today() - min_date).days)
    months_active = max(1.0, days_active / 30.0)
    
    # Net monthly savings rate (INR)
    monthly_savings = max(0.0, (total_inc - total_exp) / months_active)
    
    # Format goals with conversion & predictions
    goals_data = []
    today = date.today()
    
    for goal in goals:
        g_dict = goal.to_dict()
        
        # Convert amounts for selected currency
        g_dict['target_amount'] = goal.target_amount / rate
        g_dict['current_amount'] = goal.current_amount / rate
        g_dict['remaining_amount'] = g_dict['target_amount'] - g_dict['current_amount']
        
        # Calculate days remaining
        days_left = (goal.deadline - today).days
        g_dict['days_left'] = max(0, days_left)
        
        # Predictions: how many months needed to save the remaining balance
        remaining_inr = goal.target_amount - goal.current_amount
        if remaining_inr <= 0:
            g_dict['prediction'] = "Goal Achieved! 🏆"
        elif monthly_savings <= 0:
            g_dict['prediction'] = "Goal out of reach at your current saving rate. Try raising income or cutting expenses."
        else:
            months_needed = remaining_inr / monthly_savings
            g_dict['prediction'] = f"Estimated {round(months_needed, 1)} months to reach target at your current net savings rate."
            
            # Forecast date
            forecast_days = int(months_needed * 30)
            forecast_date = today + timedelta_custom(forecast_days)
            g_dict['forecast_date'] = forecast_date.strftime('%B %Y')
            
            # If forecast date is past deadline
            if today + timedelta_custom(forecast_days) > goal.deadline:
                g_dict['status_warning'] = True
                
        goals_data.append(g_dict)
        
    symbol = '₹'
    if user.currency == 'USD': symbol = '$'
    elif user.currency == 'EUR': symbol = '€'
    elif user.currency == 'GBP': symbol = '£'
    
    return render_template('savings.html',
                           user=user,
                           goals=goals_data,
                           currency_symbol=symbol,
                           monthly_savings=monthly_savings / rate)

def timedelta_custom(days):
    from datetime import timedelta
    return timedelta(days=days)

@savings_bp.route('/savings/add', methods=['POST'])
@token_required
def add():
    user = g.current_user
    rate = get_currency_rate(user.currency)
    
    title = request.form.get('title', '').strip()
    target_amount = request.form.get('target_amount')
    current_amount = request.form.get('current_amount', '0')
    deadline_str = request.form.get('deadline')
    
    if not title or not target_amount or not deadline_str:
        flash("Required fields are missing.", "danger")
        return redirect(url_for('savings.index'))
        
    try:
        target_val = float(target_amount) * rate
        current_val = float(current_amount) * rate
        deadline_val = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid target, current amount or deadline date.", "danger")
        return redirect(url_for('savings.index'))
        
    new_goal = SavingsGoal(
        user_id=user.id,
        title=title,
        target_amount=target_val,
        current_amount=current_val,
        deadline=deadline_val
    )
    
    try:
        db.session.add(new_goal)
        db.session.commit()
        
        # Check if goal was already achieved on creation
        if current_val >= target_val:
            from services.email_service import send_savings_goal_email
            send_savings_goal_email(user.email, user.name, title, target_val)
            flash("🏆 Congratulations! Savings Goal achieved and saved!", "success")
        else:
            flash("Savings goal created successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to create savings goal: {str(e)}", "danger")
        
    return redirect(url_for('savings.index'))

@savings_bp.route('/savings/edit/<int:id>', methods=['POST'])
@token_required
def edit(id):
    user = g.current_user
    rate = get_currency_rate(user.currency)
    goal = SavingsGoal.query.filter_by(id=id, user_id=user.id).first_or_404()
    
    title = request.form.get('title', '').strip()
    target_amount = request.form.get('target_amount')
    current_amount = request.form.get('current_amount')
    deadline_str = request.form.get('deadline')
    
    if not title or not target_amount or not deadline_str:
        flash("Required fields are missing.", "danger")
        return redirect(url_for('savings.index'))
        
    try:
        target_val = float(target_amount) * rate
        current_val = float(current_amount) * rate
        deadline_val = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid amount values or deadline format.", "danger")
        return redirect(url_for('savings.index'))
        
    old_achieved = goal.current_amount >= goal.target_amount
    
    goal.title = title
    goal.target_amount = target_val
    goal.current_amount = current_val
    goal.deadline = deadline_val
    
    try:
        db.session.commit()
        
        # Trigger notification if goals transitions to achieved
        new_achieved = current_val >= target_val
        if new_achieved and not old_achieved:
            from services.email_service import send_savings_goal_email
            send_savings_goal_email(user.email, user.name, title, target_val)
            flash("🏆 Goal Achieved! A confirmation milestone alert has been triggered.", "success")
        else:
            flash("Savings Goal modified successfully.", "success")
            
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update savings goal: {str(e)}", "danger")
        
    return redirect(url_for('savings.index'))

@savings_bp.route('/savings/delete/<int:id>', methods=['POST'])
@token_required
def delete(id):
    user = g.current_user
    goal = SavingsGoal.query.filter_by(id=id, user_id=user.id).first_or_404()
    
    try:
        db.session.delete(goal)
        db.session.commit()
        flash("Savings goal deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Deletion failed: {str(e)}", "danger")
        
    return redirect(url_for('savings.index'))
