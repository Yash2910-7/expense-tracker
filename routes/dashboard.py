from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, g, flash
from models import db
from models.expense import Expense
from models.income import Income
from models.savings import SavingsGoal
from models.recurring import RecurringExpense
from routes.auth import token_required
from ml.spending_predictor import predict_future_spending
from ml.anomaly_detector import detect_anomaly
from ml.insights_generator import generate_ai_insights, calculate_financial_health_score, get_monthly_challenges

dashboard_bp = Blueprint('dashboard', __name__)

def get_currency_details(currency_code):
    """Returns currency symbol and exchange rate relative to INR (base)."""
    rates = {
        'INR': ('₹', 1.0),
        'USD': ('$', 83.0),
        'EUR': ('€', 90.0),
        'GBP': ('£', 105.0)
    }
    return rates.get(currency_code, ('₹', 1.0))

def process_recurring_expenses(user_id):
    """
    Checks active recurring expenses and auto-creates transaction records
    if their frequency interval has passed since last_posted or creation date.
    """
    today = date.today()
    active_recurrings = RecurringExpense.query.filter_by(user_id=user_id, is_active=True).all()
    posted_count = 0
    
    for item in active_recurrings:
        start_date = item.last_posted or item.created_at.date()
        next_due = None
        
        # Calculate next due date
        if item.frequency == 'Daily':
            next_due = start_date + timedelta(days=1)
        elif item.frequency == 'Weekly':
            next_due = start_date + timedelta(weeks=1)
        elif item.frequency == 'Monthly':
            next_due = start_date + timedelta(days=30)
            
        # If due dates are in the past or today, we need to post them
        while next_due and next_due <= today:
            # Create a regular expense entry
            new_exp = Expense(
                user_id=user_id,
                category=item.category,
                amount=item.amount,
                description=f"{item.description or ''} [Auto-recurring {item.frequency}]".strip(),
                date=next_due
            )
            db.session.add(new_exp)
            
            # Move index forward
            item.last_posted = next_due
            posted_count += 1
            
            if item.frequency == 'Daily':
                next_due = next_due + timedelta(days=1)
            elif item.frequency == 'Weekly':
                next_due = next_due + timedelta(weeks=1)
            elif item.frequency == 'Monthly':
                next_due = next_due + timedelta(days=30)
                
    if posted_count > 0:
        try:
            db.session.commit()
            flash(f"⚙️ Auto-posted {posted_count} recurring bills to your transaction log.", "info")
        except Exception as e:
            db.session.rollback()
            print(f"Failed to post recurring expenses: {e}")

@dashboard_bp.route('/')
@token_required
def index():
    user = g.current_user
    
    # Process recurring items first
    process_recurring_expenses(user.id)
    
    # Get active currency symbol and exchange rate
    symbol, rate = get_currency_details(user.currency)
    
    # Load all user records
    user_expenses = Expense.query.filter_by(user_id=user.id).order_by(Expense.date.desc()).all()
    user_incomes = Income.query.filter_by(user_id=user.id).order_by(Income.date.desc()).all()
    user_goals = SavingsGoal.query.filter_by(user_id=user.id).all()
    
    # Aggregations
    total_exp_converted = sum(e.amount / rate for e in user_expenses)
    total_inc_converted = sum(i.amount / rate for i in user_incomes)
    total_savings_converted = sum(goal.current_amount / rate for goal in user_goals)
    
    # Monthly numbers
    current_month_prefix = datetime.now().strftime("%Y-%m")
    last_month_prefix = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    
    this_month_expenses = [e for e in user_expenses if e.date.strftime("%Y-%m") == current_month_prefix]
    this_month_exp_val = sum(e.amount for e in this_month_expenses)
    
    last_month_expenses = [e for e in user_expenses if e.date.strftime("%Y-%m") == last_month_prefix]
    last_month_exp_val = sum(e.amount for e in last_month_expenses)
    
    # Budget tracking
    budget_converted = user.global_budget / rate
    this_month_spent_converted = this_month_exp_val / rate
    remaining_budget = budget_converted - this_month_spent_converted
    
    # Monthly growth rate
    growth_pct = 0.0
    if last_month_exp_val > 0:
        growth_pct = ((this_month_exp_val - last_month_exp_val) / last_month_exp_val) * 100
        
    # ML features
    predictions = predict_future_spending(user_expenses)
    # Convert predictions to selected currency
    if isinstance(predictions['next_week'], (int, float)):
        predictions['next_week'] = round(predictions['next_week'] / rate, 2)
    if isinstance(predictions['next_month'], (int, float)):
        predictions['next_month'] = round(predictions['next_month'] / rate, 2)
        
    ai_insights = generate_ai_insights(user_expenses, user_incomes, user_goals, user.global_budget, symbol)
    health_score = calculate_financial_health_score(user_expenses, user_incomes, user.global_budget)
    
    # Aggregates for charts
    category_summary = {}
    for exp in user_expenses:
        category_summary[exp.category] = category_summary.get(exp.category, 0.0) + (exp.amount / rate)
        
    monthly_summary = {}
    for exp in user_expenses:
        month = exp.date.strftime("%Y-%m")
        monthly_summary[month] = monthly_summary.get(month, 0.0) + (exp.amount / rate)
        
    daily_summary = {}
    for exp in this_month_expenses:
        day = exp.date.strftime("%d")
        daily_summary[day] = daily_summary.get(day, 0.0) + (exp.amount / rate)
        
    # Income vs Expense chart data
    income_by_month = {}
    for inc in user_incomes:
        month = inc.date.strftime("%Y-%m")
        income_by_month[month] = income_by_month.get(month, 0.0) + (inc.amount / rate)
        
    # Get last 5 transactions
    recent_transactions = [{
        'id': e.id,
        'date': e.date.strftime('%Y-%m-%d'),
        'category': e.category,
        'description': e.description,
        'amount': e.amount / rate,
        'receipt': e.receipt_filename
    } for e in user_expenses[:5]]
    
    return render_template('dashboard.html',
                           user=user,
                           currency_symbol=symbol,
                           total_expenses=total_exp_converted,
                           total_income=total_inc_converted,
                           total_savings=total_savings_converted,
                           budget=budget_converted,
                           remaining_budget=remaining_budget,
                           growth_pct=growth_pct,
                           this_month_spent=this_month_spent_converted,
                           predictions=predictions,
                           ai_insights=ai_insights,
                           health_score=health_score,
                           category_summary=category_summary,
                           monthly_summary=monthly_summary,
                           daily_summary=daily_summary,
                           income_by_month=income_by_month,
                           recent_transactions=recent_transactions)

@dashboard_bp.route('/calendar')
@token_required
def calendar_view():
    user = g.current_user
    symbol, rate = get_currency_details(user.currency)
    return render_template('calendar.html', user=user, currency_symbol=symbol)

@dashboard_bp.route('/budget-planner')
@token_required
def budget_planner():
    user = g.current_user
    symbol, rate = get_currency_details(user.currency)
    budget_converted = user.global_budget / rate
    
    # Calculate category expenses for recommendations
    user_expenses = Expense.query.filter_by(user_id=user.id).all()
    category_summary = {}
    for exp in user_expenses:
        category_summary[exp.category] = category_summary.get(exp.category, 0.0) + (exp.amount / rate)
        
    return render_template('budget_planner.html',
                           user=user,
                           currency_symbol=symbol,
                           budget=budget_converted,
                           category_summary=category_summary)

@dashboard_bp.route('/challenges')
@token_required
def challenges_view():
    user = g.current_user
    symbol, rate = get_currency_details(user.currency)
    user_expenses = Expense.query.filter_by(user_id=user.id).all()
    challenges = get_monthly_challenges(user_expenses)
    
    return render_template('challenges.html',
                           user=user,
                           currency_symbol=symbol,
                           challenges=challenges)
