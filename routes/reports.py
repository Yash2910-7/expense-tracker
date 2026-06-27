import os
import io
import csv
from datetime import datetime, date
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend to prevent GUI errors
import matplotlib.pyplot as plt

from flask import Blueprint, render_template, request, Response, send_file, g, flash, redirect, url_for
from models import db
from models.expense import Expense
from models.income import Income
from models.savings import SavingsGoal
from routes.auth import token_required
from ml.insights_generator import generate_ai_insights, calculate_financial_health_score
from config import Config

# ReportLab imports for professional PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

reports_bp = Blueprint('reports', __name__)

def get_currency_details(currency_code):
    rates = {
        'INR': ('₹', 1.0),
        'USD': ('$', 83.0),
        'EUR': ('€', 90.0),
        'GBP': ('£', 105.0)
    }
    return rates.get(currency_code, ('₹', 1.0))

@reports_bp.route('/reports')
@token_required
def index():
    user = g.current_user
    symbol, rate = get_currency_details(user.currency)
    
    # Simple templates stats
    total_exp = sum(e.amount for e in Expense.query.filter_by(user_id=user.id).all())
    total_inc = sum(i.amount for i in Income.query.filter_by(user_id=user.id).all())
    
    return render_template('reports.html',
                           user=user,
                           currency_symbol=symbol,
                           total_income=total_inc / rate,
                           total_expenses=total_exp / rate)

@reports_bp.route('/reports/csv')
@token_required
def export_csv():
    try:
        user = g.current_user
        symbol, rate = get_currency_details(user.currency)
        
        expenses = Expense.query.filter_by(user_id=user.id).order_by(Expense.date.desc()).all()
        incomes = Income.query.filter_by(user_id=user.id).order_by(Income.date.desc()).all()
        
        # Create string buffer
        si = io.StringIO()
        cw = csv.writer(si)
        
        # Write Title Details
        cw.writerow([f"Smart Expense Tracker Report for {user.name} ({user.email})"])
        cw.writerow([f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
        cw.writerow([f"Active Currency: {user.currency} ({symbol})"])
        cw.writerow([])
        
        # Write Income segment
        cw.writerow(["=== INCOME TRANSACTIONS ==="])
        cw.writerow(["Date", "Source", "Description", f"Amount ({user.currency})", "Amount (INR Base)"])
        for inc in incomes:
            cw.writerow([
                inc.date.strftime('%Y-%m-%d'),
                inc.source,
                inc.description or '',
                f"{inc.amount / rate:.2f}",
                f"{inc.amount:.2f}"
            ])
        cw.writerow([])
        
        # Write Expenses segment
        cw.writerow(["=== EXPENSE TRANSACTIONS ==="])
        cw.writerow(["Date", "Category", "Description", f"Amount ({user.currency})", "Amount (INR Base)", "Receipt File"])
        for exp in expenses:
            cw.writerow([
                exp.date.strftime('%Y-%m-%d'),
                exp.category,
                exp.description or '',
                f"{exp.amount / rate:.2f}",
                f"{exp.amount:.2f}",
                exp.receipt_filename or 'None'
            ])
            
        output = si.getvalue()
        
        clean_name = "".join(c for c in user.name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        if not clean_name:
            clean_name = "user"
            
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename={clean_name}_financial_report.csv"}
        )
    except Exception as e:
        flash(f"CSV export failed: {str(e)}", "danger")
        return redirect(url_for('reports.index'))

@reports_bp.route('/reports/pdf')
@token_required
def export_pdf():
    try:
        user = g.current_user
        symbol, rate = get_currency_details(user.currency)
        
        # Load User Records
        expenses = Expense.query.filter_by(user_id=user.id).order_by(Expense.date.desc()).all()
        incomes = Income.query.filter_by(user_id=user.id).order_by(Income.date.desc()).all()
        goals = SavingsGoal.query.filter_by(user_id=user.id).all()
        
        # Basic Calculations
        total_exp_val = sum(e.amount for e in expenses)
        total_inc_val = sum(i.amount for i in incomes)
        net_savings = total_inc_val - total_exp_val
        health_score = calculate_financial_health_score(expenses, incomes, user.global_budget)
        
        # Create Matplotlib charts in memory
        chart_image_buffer = None
        if expenses:
            try:
                # Aggregate expense amounts by category for the pie chart
                cat_totals = {}
                for e in expenses:
                    cat_totals[e.category] = cat_totals.get(e.category, 0.0) + (e.amount / rate)
                    
                plt.figure(figsize=(6, 4))
                # Clean emojis for matplotlib display compatibility
                labels = []
                for cat in cat_totals.keys():
                    clean_cat = cat.split()[-1] if len(cat.split()) > 1 else cat
                    labels.append(clean_cat)
                    
                colors_list = ['#4f46e5', '#06b6d4', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#3b82f6']
                plt.pie(cat_totals.values(), labels=labels, autopct='%1.1f%%', colors=colors_list[:len(labels)], startangle=140)
                plt.title('Spending Distribution by Category', fontsize=12, fontweight='bold', pad=15)
                plt.tight_layout()
                
                # Save chart to memory buffer
                chart_image_buffer = io.BytesIO()
                plt.savefig(chart_image_buffer, format='png', dpi=150)
                plt.close()
                chart_image_buffer.seek(0)
            except Exception as e:
                print(f"Failed to generate PDF matplotlib chart: {e}")
                plt.close()
                chart_image_buffer = None

        # Setup ReportLab Document Buffer in Memory
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter,
                                rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
        
        styles = getSampleStyleSheet()
        
        # Custom Palette Colors
        PRIMARY_COLOR = colors.HexColor("#1e1b4b")  # Deep Blue Indigo
        ACCENT_COLOR = colors.HexColor("#4f46e5")   # Royal Indigo
        TEXT_COLOR = colors.HexColor("#334155")     # Slate Gray Text
        
        # Custom Paragraph Styles
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=24,
            textColor=PRIMARY_COLOR,
            spaceAfter=15
        )
        subtitle_style = ParagraphStyle(
            'DocSubTitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=20
        )
        heading2_style = ParagraphStyle(
            'Heading2',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=ACCENT_COLOR,
            spaceBefore=15,
            spaceAfter=10
        )
        body_style = ParagraphStyle(
            'BodyText',
            parent=styles['BodyText'],
            fontName='Helvetica',
            fontSize=10,
            textColor=TEXT_COLOR,
            leading=14
        )
        
        story = []
        
        # 1. Document Header
        story.append(Paragraph("Smart Expense Tracker AI", title_style))
        story.append(Paragraph(f"Monthly Wealth Audit Report for {user.name} | Date Generated: {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
        story.append(Spacer(1, 10))
        
        # 2. Executive Summary Metrics Table
        summary_data = [
            [Paragraph("<b>Financial Metric</b>", body_style), Paragraph("<b>Converted Amount ({})</b>".format(user.currency), body_style), Paragraph("<b>Base INR</b>", body_style)],
            [Paragraph("Total Income Tracking", body_style), Paragraph(f"{symbol}{total_inc_val / rate:,.2f}", body_style), Paragraph(f"₹{total_inc_val:,.2f}", body_style)],
            [Paragraph("Total Expenses Tracking", body_style), Paragraph(f"{symbol}{total_exp_val / rate:,.2f}", body_style), Paragraph(f"₹{total_exp_val:,.2f}", body_style)],
            [Paragraph("Net Savings", body_style), Paragraph(f"{symbol}{net_savings / rate:,.2f}", body_style), Paragraph(f"₹{net_savings:,.2f}", body_style)],
            [Paragraph("Financial Health Score", body_style), Paragraph(f"<b>{health_score}/100</b>", body_style), Paragraph("N/A", body_style)]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 2.0*inch, 2.0*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
            ('TEXTCOLOR', (0,0), (-1,0), PRIMARY_COLOR),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')
        ]))
        
        story.append(Paragraph("Executive Overview", heading2_style))
        story.append(summary_table)
        story.append(Spacer(1, 15))
        
        # 3. AI recommendations
        story.append(Paragraph("AI Spending Recommendations", heading2_style))
        ai_insights = generate_ai_insights(expenses, incomes, goals, user.global_budget, symbol)
        for insight in ai_insights:
            story.append(Paragraph(f"• {insight}", body_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 15))
        
        # 4. Expense Chart and Summary Data (side-by-side or stacked layout)
        if chart_image_buffer:
            story.append(Paragraph("Spending Analytics Visualization", heading2_style))
            # Embed chart image (scaling for pdf boundary fitting)
            img = Image(chart_image_buffer, width=4.5*inch, height=3.0*inch)
            story.append(img)
            story.append(Spacer(1, 15))
            
        # 5. Recent Transaction List Table
        if expenses:
            story.append(Paragraph("Recent Expense Ledger (Base Currencies)", heading2_style))
            ledger_data = [
                [Paragraph("<b>Date</b>", body_style), Paragraph("<b>Category</b>", body_style), Paragraph("<b>Description</b>", body_style), Paragraph("<b>Amount ({})</b>".format(user.currency), body_style)]
            ]
            
            # Pull last 10 transactions
            for e in expenses[:10]:
                clean_cat = e.category.split()[-1] if len(e.category.split()) > 1 else e.category
                ledger_data.append([
                    Paragraph(e.date.strftime('%Y-%m-%d'), body_style),
                    Paragraph(clean_cat, body_style),
                    Paragraph(e.description or 'No notes', body_style),
                    Paragraph(f"{symbol}{e.amount / rate:,.2f}", body_style)
                ])
                
            ledger_table = Table(ledger_data, colWidths=[1.2*inch, 1.5*inch, 2.8*inch, 1.2*inch])
            ledger_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
                ('TEXTCOLOR', (0,0), (-1,0), PRIMARY_COLOR),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")])
            ]))
            story.append(ledger_table)
            
        # Build Document in memory
        doc.build(story)
        
        pdf_buffer.seek(0)
        
        clean_name = "".join(c for c in user.name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        if not clean_name:
            clean_name = "user"
            
        pdf_filename = f"{clean_name}_financial_report.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=pdf_filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"PDF generation failed: {str(e)}", "danger")
        return redirect(url_for('reports.index'))
