import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import Config

def send_email(to_email, subject, html_body):
    """
    Sends an HTML email. Falls back to logging the email to a file
    in 'reports/simulated_emails.log' if SMTP credentials are not set.
    """
    # Check if SMTP parameters are configured
    is_configured = bool(Config.SMTP_USER and Config.SMTP_PASSWORD and Config.SENDER_EMAIL)
    
    if is_configured:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = Config.SENDER_EMAIL
            msg['To'] = to_email
            
            part = MIMEText(html_body, 'html')
            msg.attach(part)
            
            # Start SMTP TLS connection
            server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            server.sendmail(Config.SENDER_EMAIL, to_email, msg.as_string())
            server.quit()
            return True, "Email sent successfully via SMTP."
        except Exception as e:
            # Fall back to simulation on SMTP failure
            log_simulated_email(to_email, subject, html_body, f"SMTP Error: {str(e)}")
            return False, f"SMTP failed: {str(e)}. Simulated email generated."
    else:
        log_simulated_email(to_email, subject, html_body, "SMTP Credentials not configured.")
        return True, "Simulated email generated (SMTP not configured)."

def log_simulated_email(to_email, subject, html_body, status):
    """Logs the email content locally for inspection and debugging."""
    reports_dir = Config.REPORTS_FOLDER
    os.makedirs(reports_dir, exist_ok=True)
    log_file = os.path.join(reports_dir, 'simulated_emails.log')
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    divider = "=" * 80
    
    log_content = f"""
{divider}
[SIMULATED EMAIL GENERATED] - {timestamp}
Status: {status}
To: {to_email}
Subject: {subject}
Content-Type: text/html
{divider}
{html_body}
{divider}
\n"""
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_content)

def send_otp_email(to_email, username, otp_code):
    subject = "Smart Expense Tracker - Password Reset OTP"
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px; background-color: #f9f9f9;">
          <h2 style="color: #4f46e5; border-bottom: 2px solid #4f46e5; padding-bottom: 10px;">Verification Code</h2>
          <p>Hello <strong>{username}</strong>,</p>
          <p>You requested a password reset for your Smart Expense Tracker account.</p>
          <p>Please use the following 6-digit One-Time Password (OTP) to reset your password. This code will expire in <strong>5 minutes</strong>.</p>
          <div style="background-color: #eef2ff; border: 1px dashed #4f46e5; padding: 15px; text-align: center; border-radius: 8px; margin: 20px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #4f46e5;">{otp_code}</span>
          </div>
          <p>If you did not request this, please ignore this email or contact support if you suspect unauthorized access.</p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
          <p style="font-size: 12px; color: #666; text-align: center;">Smart Expense Tracker AI - Secure Financial Insights</p>
        </div>
      </body>
    </html>
    """
    return send_email(to_email, subject, html_body)

def send_budget_warning_email(to_email, username, category, limit, spent):
    subject = f"⚠️ Budget Limit Exceeded - {category}"
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px; background-color: #fffbfb; border-top: 4px solid #ef4444;">
          <h2 style="color: #ef4444; border-bottom: 1px solid #fee2e2; padding-bottom: 10px;">Budget Alert</h2>
          <p>Hello <strong>{username}</strong>,</p>
          <p>This is an automated alert that you have exceeded your spending budget for <strong>{category}</strong>.</p>
          <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="background-color: #fdf2f2;">
              <th style="padding: 10px; border: 1px solid #fecaca; text-align: left;">Category</th>
              <td style="padding: 10px; border: 1px solid #fecaca;">{category}</td>
            </tr>
            <tr>
              <th style="padding: 10px; border: 1px solid #eee; text-align: left;">Monthly Limit</th>
              <td style="padding: 10px; border: 1px solid #eee; font-weight: bold; color: #3b82f6;">₹{limit:,.2f}</td>
            </tr>
            <tr style="background-color: #fdf2f2;">
              <th style="padding: 10px; border: 1px solid #fecaca; text-align: left;">Current Spending</th>
              <td style="padding: 10px; border: 1px solid #fecaca; font-weight: bold; color: #ef4444;">₹{spent:,.2f}</td>
            </tr>
            <tr>
              <th style="padding: 10px; border: 1px solid #eee; text-align: left;">Overspent Amount</th>
              <td style="padding: 10px; border: 1px solid #eee; font-weight: bold; color: #b91c1c;">₹{max(0.0, spent - limit):,.2f}</td>
            </tr>
          </table>
          <p>Please review your dashboard and plan future expenses carefully to regain financial balance.</p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
          <p style="font-size: 12px; color: #666; text-align: center;">Smart Expense Tracker AI - Active Budget Advisor</p>
        </div>
      </body>
    </html>
    """
    return send_email(to_email, subject, html_body)

def send_savings_goal_email(to_email, username, goal_title, target):
    subject = f"🏆 Goal Achieved! - {goal_title}"
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px; background-color: #f0fdf4; border-top: 4px solid #22c55e;">
          <h2 style="color: #22c55e; text-align: center;">Congratulations! 🎉</h2>
          <p>Hello <strong>{username}</strong>,</p>
          <p>Outstanding effort! You have reached your savings goal: <strong>"{goal_title}"</strong>!</p>
          <div style="background-color: #dcfce7; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
            <p style="font-size: 16px; margin: 0; color: #14532d;">Target Amount Saved</p>
            <h3 style="font-size: 36px; margin: 10px 0; color: #15803d;">₹{target:,.2f}</h3>
            <span style="font-size: 14px; font-weight: bold; color: #166534; border: 1px solid #86efac; background: #fff; padding: 5px 15px; border-radius: 20px;">100% Completed</span>
          </div>
          <p>Your disciplined financial habits are paying off. Continue setting new targets and building wealth!</p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
          <p style="font-size: 12px; color: #666; text-align: center;">Smart Expense Tracker AI - Financial Milestone Tracking</p>
        </div>
      </body>
    </html>
    """
    return send_email(to_email, subject, html_body)
