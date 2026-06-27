from flask import Blueprint, request, jsonify, g
from models import db
from models.expense import Expense
from models.user import User
from routes.auth import token_required
from datetime import datetime

api_bp = Blueprint('api', __name__)

def get_currency_rate(currency_code):
    rates = {'INR': 1.0, 'USD': 83.0, 'EUR': 90.0, 'GBP': 105.0}
    return rates.get(currency_code, 1.0)

@api_bp.route('/api/currency', methods=['POST'])
@token_required
def update_currency():
    """Updates the user's selected active display currency."""
    user = g.current_user
    data = request.get_json() or {}
    currency_code = data.get('currency')
    
    if currency_code in ['INR', 'USD', 'EUR', 'GBP']:
        user.currency = currency_code
        try:
            db.session.commit()
            return jsonify({'success': True, 'currency': currency_code})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
            
    return jsonify({'success': False, 'message': 'Invalid currency code'}), 400

@api_bp.route('/api/theme', methods=['POST'])
@token_required
def update_theme():
    """Updates the user's saved UI theme preference (dark/light)."""
    user = g.current_user
    data = request.get_json() or {}
    theme = data.get('theme')
    
    if theme in ['dark', 'light']:
        user.theme = theme
        try:
            db.session.commit()
            return jsonify({'success': True, 'theme': theme})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
            
    return jsonify({'success': False, 'message': 'Invalid theme value'}), 400

@api_bp.route('/api/budget', methods=['POST'])
@token_required
def update_budget():
    """Updates the global monthly budget target."""
    user = g.current_user
    # Support both JSON request and form post
    data = request.get_json() or {}
    new_budget = data.get('budget')
    
    if new_budget is None:
        new_budget = request.form.get('new_budget')
        
    if new_budget is not None:
        try:
            # We assume input in current currency, convert to INR base database column
            rate = get_currency_rate(user.currency)
            user.global_budget = float(new_budget) * rate
            db.session.commit()
            return jsonify({'success': True, 'budget': float(new_budget)})
        except (ValueError, Exception) as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
            
    return jsonify({'success': False, 'message': 'No budget provided'}), 400

@api_bp.route('/api/calendar-events', methods=['GET'])
@token_required
def calendar_events():
    """Returns the user's daily transaction totals formatted for FullCalendar.js."""
    user = g.current_user
    rate = get_currency_rate(user.currency)
    
    # Load all user expenses
    expenses = Expense.query.filter_by(user_id=user.id).all()
    
    # Group by date
    daily_aggregates = {}
    for exp in expenses:
        date_str = exp.date.strftime('%Y-%m-%d')
        daily_aggregates[date_str] = daily_aggregates.get(date_str, 0.0) + exp.amount
        
    events = []
    symbol = '₹'
    if user.currency == 'USD': symbol = '$'
    elif user.currency == 'EUR': symbol = '€'
    elif user.currency == 'GBP': symbol = '£'
    
    # Format as FullCalendar events
    for date_str, amount in daily_aggregates.items():
        converted_amt = amount / rate
        events.append({
            'title': f"{symbol}{converted_amt:,.2f}",
            'start': date_str,
            'color': '#ef4444' if converted_amt > (user.global_budget / rate / 30) else '#4f46e5'
        })
        
    return jsonify(events)
