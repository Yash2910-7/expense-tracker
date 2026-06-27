import re
import random
from datetime import datetime, timedelta
import jwt
from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, g, session
from models import db
from models.user import User
from config import Config
from services.email_service import send_otp_email
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def encode_auth_token(user_id):
    """Generates a secure JWT token for the user."""
    try:
        payload = {
            'exp': datetime.utcnow() + timedelta(days=1),
            'iat': datetime.utcnow(),
            'sub': str(user_id)  # PyJWT 2.x requires subject (sub) to be a string
        }
        return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')
    except Exception as e:
        return str(e)

def decode_auth_token(auth_token):
    """Decodes a JWT token. Returns user_id as integer if valid, or an error string."""
    try:
        payload = jwt.decode(auth_token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        return int(payload['sub'])
    except jwt.ExpiredSignatureError:
        return 'Session expired. Please log in again.'
    except jwt.InvalidTokenError:
        return 'Session invalid. Please log in again.'

def token_required(f):
    """Route decorator to enforce JWT verification."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('auth_token')
        if not token:
            return redirect(url_for('auth.login'))
            
        user_id = decode_auth_token(token)
        if isinstance(user_id, str):
            # If string returned, it means token decode failed (expired or invalid)
            flash(user_id, "warning")
            response = make_response(redirect(url_for('auth.login')))
            response.delete_cookie('auth_token')
            return response
            
        try:
            current_user = User.query.get(user_id)
            if not current_user:
                flash("User session not found.", "warning")
                response = make_response(redirect(url_for('auth.login')))
                response.delete_cookie('auth_token')
                return response
        except Exception as e:
            # If the database is down or tables are missing, don't crash with 500!
            print(f"Database error in token verification: {e}")
            flash("Database connection error. Please try logging in again.", "danger")
            response = make_response(redirect(url_for('auth.login')))
            response.delete_cookie('auth_token')
            return response
            
        g.current_user = current_user
        return f(*args, **kwargs)
    return decorated

def validate_password_strength(password):
    """Enforces password complexity rules."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search("[a-z]", password):
        return False, "Password must contain at least one lowercase character."
    if not re.search("[A-Z]", password):
        return False, "Password must contain at least one uppercase character."
    if not re.search("[0-9]", password):
        return False, "Password must contain at least one numeric digit."
    if not re.search("[_@$!%*#?&+-]", password):
        return False, "Password must contain at least one special character (_@$!%*#?&+-)."
    return True, ""

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.cookies.get('auth_token'):
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Validations
        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template('register.html')
            
        # Email uniqueness
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email address is already registered.", "danger")
            return render_template('register.html')
            
        # Password strength validation
        is_strong, err_msg = validate_password_strength(password)
        if not is_strong:
            flash(err_msg, "danger")
            return render_template('register.html')
            
        # Create and save user
        new_user = User(name=name, email=email)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Account registered successfully! Please log in.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f"Registration failed: {str(e)}", "danger")
            
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.cookies.get('auth_token'):
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            # Successful authentication: generate token
            token = encode_auth_token(user.id)
            
            # Setup response and cookie
            response = make_response(redirect(url_for('dashboard.index')))
            response.set_cookie('auth_token', token, httponly=True, max_age=86400) # 1 day expiry
            flash(f"Welcome back, {user.name}!", "success")
            return response
        else:
            flash("Invalid email or password.", "danger")
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    response = make_response(redirect(url_for('auth.login')))
    response.delete_cookie('auth_token')
    flash("You have logged out successfully.", "info")
    return response

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate a 6-digit random OTP code
            otp = f"{random.randint(100000, 999999)}"
            user.otp_code = otp
            user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
            
            try:
                db.session.commit()
                # Send OTP via email service
                send_otp_email(user.email, user.name, otp)
                session['reset_email'] = user.email
                flash("A 6-digit verification code has been generated and dispatched to your email address.", "info")
                return redirect(url_for('auth.verify_otp'))
            except Exception as e:
                db.session.rollback()
                flash(f"Failed to generate recovery OTP: {str(e)}", "danger")
        else:
            flash("No account matches that email address.", "danger")
            
    return render_template('forgot_password.html')

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    reset_email = session.get('reset_email')
    if not reset_email:
        flash("Password recovery session expired.", "warning")
        return redirect(url_for('auth.forgot_password'))
        
    if request.method == 'POST':
        otp_input = request.form.get('otp', '').strip()
        user = User.query.filter_by(email=reset_email).first()
        
        if user and user.otp_code == otp_input:
            if datetime.utcnow() <= user.otp_expiry:
                session['otp_verified'] = True
                flash("OTP code verified! Please set a new password.", "success")
                return redirect(url_for('auth.reset_password'))
            else:
                flash("This verification code has expired. Please request a new one.", "danger")
        else:
            flash("Invalid verification code. Please try again.", "danger")
            
    return render_template('otp_verification.html', email=reset_email)

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if not session.get('otp_verified') or not session.get('reset_email'):
        flash("Unauthorized reset attempt.", "warning")
        return redirect(url_for('auth.forgot_password'))
        
    reset_email = session.get('reset_email')
    
    if request.method == 'POST':
        new_password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('reset_password.html')
            
        is_strong, err_msg = validate_password_strength(new_password)
        if not is_strong:
            flash(err_msg, "danger")
            return render_template('reset_password.html')
            
        user = User.query.filter_by(email=reset_email).first()
        if user:
            user.set_password(new_password)
            user.otp_code = None
            user.otp_expiry = None
            
            try:
                db.session.commit()
                # Clear security session variables
                session.pop('reset_email', None)
                session.pop('otp_verified', None)
                flash("Your password has been successfully reset. You can now log in.", "success")
                return redirect(url_for('auth.login'))
            except Exception as e:
                db.session.rollback()
                flash(f"Failed to update password: {str(e)}", "danger")
                
    return render_template('reset_password.html')

# MOCK GOOGLE OAUTH FLOW
@auth_bp.route('/google')
def google_auth():
    # If client secrets are set, we would implement the real OAuth2 logic.
    # Otherwise, redirect to a beautiful Mock login page for internship demonstration.
    if Config.GOOGLE_CLIENT_ID and Config.GOOGLE_CLIENT_SECRET:
        # Standard implementation (redirecting to Google)
        # For simplicity of demo, we direct to mock flow if not configured
        pass
        
    return redirect(url_for('auth.google_mock_page'))

@auth_bp.route('/google/mock-consent', methods=['GET', 'POST'])
def google_mock_page():
    if request.method == 'POST':
        # Simulated Google Consent page form submit
        name = request.form.get('name', 'Alex Finance').strip()
        email = request.form.get('email', 'alex.finance@gmail.com').strip().lower()
        
        # Check if user exists, otherwise create
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email)
            user.set_password(f"GoogleUser_{random.randint(1000,9999)}A!") # Secure default pass
            db.session.add(user)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(f"OAuth signup failed: {str(e)}", "danger")
                return redirect(url_for('auth.login'))
                
        # Generate token and login user
        token = encode_auth_token(user.id)
        response = make_response(redirect(url_for('dashboard.index')))
        response.set_cookie('auth_token', token, httponly=True, max_age=86400)
        flash(f"Logged in via Google OAuth as {user.name}!", "success")
        return response
        
    return render_template('google_mock.html')
