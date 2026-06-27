import os
import psycopg2
from urllib.parse import urlparse
from flask import Flask, redirect, url_for, request
from config import Config
from models import db
from models.user import User
from models.expense import Expense
from models.income import Income
from models.savings import SavingsGoal
from models.recurring import RecurringExpense

def check_and_prepare_postgres(db_url):
    """
    Checks if PostgreSQL connection details are active, connects to the
    default 'postgres' database, and creates the target database if missing.
    Returns True if connection succeeded and database is ready, False otherwise.
    """
    if not db_url.startswith('postgresql'):
        return False
        
    try:
        result = urlparse(db_url)
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port or 5432
        
        # Connect to default system DB to verify server and create target DB
        conn = psycopg2.connect(
            dbname='postgres',
            user=username,
            password=password,
            host=hostname,
            port=port,
            connect_timeout=3
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if target database exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{database}';")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f"CREATE DATABASE {database};")
            print(f"PostgreSQL: Database '{database}' created successfully.")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"PostgreSQL connection verification failed: {e}")
        return False

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Verify and prepare PostgreSQL database, or fall back to SQLite
    db_uri = Config.SQLALCHEMY_DATABASE_URI
    is_postgres_ready = check_and_prepare_postgres(db_uri)
    
    if not is_postgres_ready:
        print("PostgreSQL was not ready or unreachable. Falling back to local SQLite...")
        db_dir = os.path.join(app.root_path, 'database')
        os.makedirs(db_dir, exist_ok=True)
        sqlite_uri = f"sqlite:///{os.path.join(db_dir, 'expense_tracker.db')}"
        app.config['SQLALCHEMY_DATABASE_URI'] = sqlite_uri
    else:
        print("PostgreSQL is verified and ready. Establishing SQLAlchemy context.")

    # Initialize extensions
    db.init_app(app)

    # Register Blueprint routes
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.expenses import expenses_bp
    from routes.income import income_bp
    from routes.savings import savings_bp
    from routes.recurring import recurring_bp
    from routes.reports import reports_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(savings_bp)
    app.register_blueprint(recurring_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp)

    @app.route('/sw.js')
    def service_worker():
        return app.send_static_file('sw.js')

    # Redirect to auth login on page errors or handle 404s
    @app.errorhandler(404)
    def page_not_found(e):
        return redirect(url_for('dashboard.index'))

    # Inject global helper context to HTML templates
    from datetime import date
    from flask import g
    @app.context_processor
    def inject_global_context():
        return {
            'user': getattr(g, 'current_user', None),
            'date_today': date.today().strftime('%Y-%m-%d')
        }

    # Initialize tables
    with app.app_context():
        try:
            db.create_all()
            print("Database schemas compiled successfully.")
        except Exception as e:
            print(f"Error during schema compilation: {e}")

    return app

app = create_app()

if __name__ == '__main__':
    # Start web server on port 5000
    app.run(debug=True)