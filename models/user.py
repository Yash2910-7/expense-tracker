from datetime import datetime
from models import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # OTP authentication properties for verification & password resets
    otp_code = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)
    
    # User preference configurations
    global_budget = db.Column(db.Float, default=5000.0)
    currency = db.Column(db.String(10), default='INR')  # INR, USD, EUR, GBP
    theme = db.Column(db.String(10), default='dark')    # dark, light
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships with other tables
    expenses = db.relationship('Expense', backref='user', lazy=True, cascade='all, delete-orphan')
    incomes = db.relationship('Income', backref='user', lazy=True, cascade='all, delete-orphan')
    savings_goals = db.relationship('SavingsGoal', backref='user', lazy=True, cascade='all, delete-orphan')
    recurring_expenses = db.relationship('RecurringExpense', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Hashes the password using Werkzeug's secure hashing."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks if hashed password matches."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'global_budget': self.global_budget,
            'currency': self.currency,
            'theme': self.theme,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
