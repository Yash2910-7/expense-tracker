from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models import db
from models.recurring import RecurringExpense
from routes.auth import token_required

recurring_bp = Blueprint('recurring', __name__)

def get_currency_rate(currency_code):
    rates = {'INR': 1.0, 'USD': 83.0, 'EUR': 90.0, 'GBP': 105.0}
    return rates.get(currency_code, 1.0)

@recurring_bp.route('/recurring', methods=['GET'])
@token_required
def index():
    user = g.current_user
    rate = get_currency_rate(user.currency)
    
    recurrings = RecurringExpense.query.filter_by(user_id=user.id).order_by(RecurringExpense.created_at.desc()).all()
    
    # Convert amounts for display
    converted_recurrings = []
    for item in recurrings:
        item_dict = item.to_dict()
        item_dict['amount'] = item.amount / rate
        converted_recurrings.append(item_dict)
        
    categories = [
        "🍔 Food", "✈️ Travel", "🛒 Shopping", "💡 Bills", "🎮 Entertainment",
        "🏥 Health", "📚 Education", "🏠 Rent", "🚗 Transport", "📱 Subscription"
    ]
    
    symbol = '₹'
    if user.currency == 'USD': symbol = '$'
    elif user.currency == 'EUR': symbol = '€'
    elif user.currency == 'GBP': symbol = '£'
    
    return render_template('recurring.html',
                           user=user,
                           recurrings=converted_recurrings,
                           categories=categories,
                           currency_symbol=symbol)

@recurring_bp.route('/recurring/add', methods=['POST'])
@token_required
def add():
    user = g.current_user
    rate = get_currency_rate(user.currency)
    
    amount = request.form.get('amount')
    category = request.form.get('category')
    frequency = request.form.get('frequency')
    description = request.form.get('description', '').strip()
    
    if not amount or not category or not frequency:
        flash("Required fields are missing.", "danger")
        return redirect(url_for('recurring.index'))
        
    try:
        amount_val = float(amount) * rate
    except ValueError:
        flash("Invalid amount.", "danger")
        return redirect(url_for('recurring.index'))
        
    new_recurring = RecurringExpense(
        user_id=user.id,
        category=category,
        amount=amount_val,
        frequency=frequency,
        description=description,
        is_active=True
    )
    
    try:
        db.session.add(new_recurring)
        db.session.commit()
        flash("Recurring expense scheduled successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to schedule recurring expense: {str(e)}", "danger")
        
    return redirect(url_for('recurring.index'))

@recurring_bp.route('/recurring/edit/<int:id>', methods=['POST'])
@token_required
def edit(id):
    user = g.current_user
    rate = get_currency_rate(user.currency)
    item = RecurringExpense.query.filter_by(id=id, user_id=user.id).first_or_404()
    
    amount = request.form.get('amount')
    category = request.form.get('category')
    frequency = request.form.get('frequency')
    description = request.form.get('description', '').strip()
    
    if not amount or not category or not frequency:
        flash("Required fields are missing.", "danger")
        return redirect(url_for('recurring.index'))
        
    try:
        amount_val = float(amount) * rate
    except ValueError:
        flash("Invalid amount.", "danger")
        return redirect(url_for('recurring.index'))
        
    item.amount = amount_val
    item.category = category
    item.frequency = frequency
    item.description = description
    
    try:
        db.session.commit()
        flash("Recurring schedule modified.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update schedule: {str(e)}", "danger")
        
    return redirect(url_for('recurring.index'))

@recurring_bp.route('/recurring/toggle/<int:id>', methods=['POST'])
@token_required
def toggle(id):
    user = g.current_user
    item = RecurringExpense.query.filter_by(id=id, user_id=user.id).first_or_404()
    
    item.is_active = not item.is_active
    
    try:
        db.session.commit()
        status = "active" if item.is_active else "paused"
        flash(f"Recurring expense schedule is now {status}.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to change status: {str(e)}", "danger")
        
    return redirect(url_for('recurring.index'))

@recurring_bp.route('/recurring/delete/<int:id>', methods=['POST'])
@token_required
def delete(id):
    user = g.current_user
    item = RecurringExpense.query.filter_by(id=id, user_id=user.id).first_or_404()
    
    try:
        db.session.delete(item)
        db.session.commit()
        flash("Recurring schedule removed.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Deletion failed: {str(e)}", "danger")
        
    return redirect(url_for('recurring.index'))
