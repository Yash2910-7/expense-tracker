from datetime import datetime, date

def calculate_financial_health_score(expenses, incomes, user_budget):
    """
    Calculates a financial health score from 0 to 100 based on:
    - Savings rate (40% weight)
    - Budget compliance (40% weight)
    - Investment ratio / income diversity (20% weight)
    """
    try:
        # Sum current month income and expenses
        current_month = datetime.now().strftime("%Y-%m")
        
        monthly_income = 0.0
        for inc in incomes:
            inc_date = inc.date if hasattr(inc, 'date') else datetime.strptime(inc['date'], '%Y-%m-%d').date()
            if inc_date.strftime("%Y-%m") == current_month:
                monthly_income += float(inc.amount if hasattr(inc, 'amount') else inc['amount'])
                
        monthly_expense = 0.0
        for exp in expenses:
            exp_date = exp.date if hasattr(exp, 'date') else datetime.strptime(exp['date'], '%Y-%m-%d').date()
            if exp_date.strftime("%Y-%m") == current_month:
                monthly_expense += float(exp.amount if hasattr(exp, 'amount') else exp['amount'])
                
        # 1. Savings Rate Score (Target: save at least 20% of income)
        savings_score = 0.0
        if monthly_income > 0:
            savings_rate = (monthly_income - monthly_expense) / monthly_income
            if savings_rate >= 0.3:
                savings_score = 100.0
            elif savings_rate > 0:
                savings_score = (savings_rate / 0.3) * 100
        else:
            # If no income, score is 50 if expenses are low, else lower
            savings_score = max(0.0, 100.0 - (monthly_expense / 100.0))
            
        # 2. Budget Compliance Score
        budget_score = 100.0
        budget = float(user_budget) if user_budget else 5000.0
        if monthly_expense > budget:
            overspent = monthly_expense - budget
            pct_over = overspent / budget
            budget_score = max(0.0, 100.0 - (pct_over * 150)) # Fast score drop on overspending
            
        # 3. Income diversity / investment score (Bonus score points)
        investment_score = 50.0 # Base score
        sources = set(inc.source if hasattr(inc, 'source') else inc['source'] for inc in incomes)
        if len(sources) >= 2:
            investment_score = 100.0
            
        # Weighted aggregate
        health_score = (savings_score * 0.4) + (budget_score * 0.4) + (investment_score * 0.2)
        return min(100, max(0, int(health_score)))
    except Exception as e:
        print(f"Health score computation error: {e}")
        return 70 # Normal default fallback

def generate_ai_insights(expenses, incomes, savings_goals, user_budget, currency_symbol="₹"):
    """
    Generates actionable financial insights and savings recommendations.
    """
    insights = []
    
    if not expenses:
        return ["Start logging your expenses to receive AI-powered spending insights!"]
        
    try:
        # Convert amounts to float and compute totals
        total_expense = sum(float(e.amount if hasattr(e, 'amount') else e['amount']) for e in expenses)
        total_income = sum(float(i.amount if hasattr(i, 'amount') else i['amount']) for i in incomes)
        
        # Categorize expenses
        cat_summary = {}
        for exp in expenses:
            cat = exp.category if hasattr(exp, 'category') else exp['category']
            amt = float(exp.amount if hasattr(exp, 'amount') else exp['amount'])
            cat_summary[cat] = cat_summary.get(cat, 0.0) + amt
            
        # 1. Category spending insights
        if total_expense > 0 and cat_summary:
            highest_category = max(cat_summary, key=cat_summary.get)
            max_amount = cat_summary[highest_category]
            pct_drain = int((max_amount / total_expense) * 100)
            
            # Remove emoji if present in category name for clean sentence formatting
            clean_cat = highest_category.split()[-1] if len(highest_category.split()) > 1 else highest_category
            
            insights.append(f"You spend {pct_drain}% of your total budget on {highest_category}. Consolidating this could free up funds.")
            
            if pct_drain > 30 and clean_cat.lower() in ['food', 'shopping', 'entertainment']:
                savings_potential = max_amount * 0.15
                insights.append(f"💡 Reduce your {highest_category} spending by 15% to save {currency_symbol}{savings_potential:,.2f} monthly.")

        # 2. Savings rate recommendation
        if total_income > 0:
            savings = total_income - total_expense
            savings_rate = (savings / total_income) * 100
            
            if savings_rate < 10:
                insights.append(f"⚠️ Your savings rate is low ({savings_rate:.1f}%). Try applying the 50/30/20 budget rule to save at least 20%.")
            elif savings_rate >= 20:
                insights.append(f"🎉 Excellent! Your savings rate is {savings_rate:.1f}%, exceeding the healthy threshold of 20%. Keep it up!")
        else:
            insights.append("Log your income source regularly to track your actual savings rates and financial growth.")

        # 3. Savings goals predictions
        if savings_goals and total_income > 0:
            monthly_savings = max(0.0, (total_income - total_expense) / 12.0) # Estimated average monthly savings rate
            # Fallback if expenses exceed income or we calculate too low
            if monthly_savings <= 0:
                monthly_savings = max(1.0, total_income * 0.1) # Assume 10% target potential
                
            for goal in savings_goals:
                title = goal.title if hasattr(goal, 'title') else goal['title']
                target = float(goal.target_amount if hasattr(goal, 'target_amount') else goal['target_amount'])
                current = float(goal.current_amount if hasattr(goal, 'current_amount') else goal['current_amount'])
                
                remaining = max(0.0, target - current)
                
                # Check target category savings to speed up
                ent_spent = cat_summary.get('🎮 Entertainment', 0.0)
                shop_spent = cat_summary.get('🛒 Shopping', 0.0)
                
                potential_boost = (ent_spent + shop_spent) * 0.20 # Save 20% on entertainment/shopping
                
                if remaining > 0 and potential_boost > 0:
                    months_saved = (remaining / (monthly_savings + potential_boost)) - (remaining / monthly_savings)
                    months_saved = abs(months_saved)
                    if months_saved > 0.5:
                        insights.append(f"🎯 You can reach your savings goal '{title}' {round(months_saved, 1)} months earlier by reducing shopping/entertainment expenses by 20%.")
                        break # Only display one goal acceleration tip at a time to prevent text overflow

        # Default insights if lists are short
        if len(insights) < 2:
            insights.append("Pro Tip: Automate your monthly savings goal contributions right after salary credit.")
            insights.append("Budget Tip: Set category spending alerts to flag early overruns before month-end.")
            
    except Exception as e:
        print(f"Insights Generation Error: {e}")
        insights = ["Monitor your categories regularly to discover savings opportunities."]
        
    return insights

def get_monthly_challenges(expenses):
    """
    Returns custom financial challenges based on user transaction behaviors.
    """
    # Default initial challenges
    challenges = [
        {"title": "No-Spend Weekend", "desc": "Do not log any Shopping or Entertainment expenses this Saturday and Sunday.", "difficulty": "Medium", "reward": "50 pts"},
        {"title": "Caffeine Reduction", "desc": "Keep Food/Beverage spending under ₹500 for the entire week.", "difficulty": "Easy", "reward": "30 pts"},
        {"title": "Budget Shield", "desc": "Stay fully under your budget threshold in all categories for 15 days.", "difficulty": "Hard", "reward": "100 pts"}
    ]
    return challenges
