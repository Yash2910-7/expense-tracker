import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor

def predict_future_spending(expenses):
    """
    Predicts next week and next month spending using RandomForestRegressor.
    Returns:
        dict: {
            'next_week': float or "Need more data",
            'next_month': float or "Need more data",
            'trend': "Upward" / "Downward" / "Stable" / "Insufficient Data"
        }
    """
    if not expenses or len(expenses) < 4:
        return {
            'next_week': "Need more data (at least 4 expenses required)",
            'next_month': "Need more data (at least 4 expenses required)",
            'trend': "Insufficient Data"
        }

    try:
        # Convert expenses list to pandas DataFrame
        data = []
        for e in expenses:
            # Handle both dictionary objects and db models
            exp_date = e.date if hasattr(e, 'date') else datetime.strptime(e['date'], '%Y-%m-%d').date()
            exp_amount = float(e.amount) if hasattr(e, 'amount') else float(e['amount'])
            data.append({
                'date': pd.to_datetime(exp_date),
                'amount': exp_amount
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('date').reset_index(drop=True)
        
        # Determine duration in days
        min_date = df['date'].min()
        max_date = df['date'].max()
        days_span = (max_date - min_date).days
        
        # Calculate daily averages for fallbacks
        total_amount = df['amount'].sum()
        daily_average = total_amount / max(1, days_span)
        
        # Fallback predictions if data span is too narrow (e.g., less than 7 days)
        if days_span < 7:
            predicted_week = round(daily_average * 7, 2)
            predicted_month = round(daily_average * 30, 2)
            return {
                'next_week': predicted_week,
                'next_month': predicted_month,
                'trend': "Stable (Based on short span average)"
            }

        # Aggregate data by week
        # Group by year-week and compute weekly total
        df['year_week'] = df['date'].dt.to_period('W').dt.start_time
        weekly_df = df.groupby('year_week')['amount'].sum().reset_index()
        weekly_df = weekly_df.sort_values('year_week').reset_index(drop=True)
        
        # Add index column for regressor features
        weekly_df['time_index'] = weekly_df.index
        weekly_df['month'] = weekly_df['year_week'].dt.month
        
        num_weeks = len(weekly_df)
        
        # If we have 3 or more weeks, train a RandomForestRegressor
        if num_weeks >= 3:
            # Construct features: time_index, month, lag_1, lag_2
            weekly_df['lag_1'] = weekly_df['amount'].shift(1)
            weekly_df['lag_2'] = weekly_df['amount'].shift(2)
            
            # Fill NaN values from lag shifts
            weekly_df['lag_1'] = weekly_df['lag_1'].fillna(weekly_df['amount'].mean())
            weekly_df['lag_2'] = weekly_df['lag_2'].fillna(weekly_df['amount'].mean())
            
            X = weekly_df[['time_index', 'month', 'lag_1', 'lag_2']]
            y = weekly_df['amount']
            
            model = RandomForestRegressor(n_estimators=50, random_state=42)
            model.fit(X, y)
            
            # Predict for the next week
            next_week_index = num_weeks
            next_week_date = weekly_df['year_week'].iloc[-1] + timedelta(weeks=1)
            next_week_month = next_week_date.month
            next_week_lag1 = weekly_df['amount'].iloc[-1]
            next_week_lag2 = weekly_df['amount'].iloc[-2] if num_weeks > 1 else weekly_df['amount'].iloc[-1]
            
            X_pred = pd.DataFrame([{
                'time_index': next_week_index,
                'month': next_week_month,
                'lag_1': next_week_lag1,
                'lag_2': next_week_lag2
            }])
            
            pred_week_val = model.predict(X_pred)[0]
            predicted_week = max(0.0, round(float(pred_week_val), 2))
            
            # Predict next month (using 4.33 times the weekly forecast or aggregating by month)
            # If we have monthly data, let's do monthly regression fallback
            df['year_month'] = df['date'].dt.to_period('M').dt.start_time
            monthly_df = df.groupby('year_month')['amount'].sum().reset_index()
            num_months = len(monthly_df)
            
            if num_months >= 3:
                # Run a monthly regressor
                monthly_df['time_index'] = monthly_df.index
                monthly_df['month'] = monthly_df['year_month'].dt.month
                monthly_df['lag_1'] = monthly_df['amount'].shift(1).fillna(monthly_df['amount'].mean())
                
                X_m = monthly_df[['time_index', 'month', 'lag_1']]
                y_m = monthly_df['amount']
                
                model_m = RandomForestRegressor(n_estimators=50, random_state=42)
                model_m.fit(X_m, y_m)
                
                next_month_index = num_months
                next_month_date = monthly_df['year_month'].iloc[-1] + timedelta(days=31)
                next_month_month = next_month_date.month
                next_month_lag1 = monthly_df['amount'].iloc[-1]
                
                X_m_pred = pd.DataFrame([{
                    'time_index': next_month_index,
                    'month': next_month_month,
                    'lag_1': next_month_lag1
                }])
                
                pred_month_val = model_m.predict(X_m_pred)[0]
                predicted_month = max(0.0, round(float(pred_month_val), 2))
            else:
                predicted_month = round(predicted_week * 4.33, 2)
                
            # Determine trend direction by comparing prediction to recent average
            recent_avg = weekly_df['amount'].tail(3).mean()
            if predicted_week > recent_avg * 1.05:
                trend = "Upward"
            elif predicted_week < recent_avg * 0.95:
                trend = "Downward"
            else:
                trend = "Stable"
                
            return {
                'next_week': predicted_week,
                'next_month': predicted_month,
                'trend': trend
            }
        else:
            # Less than 3 weeks of data, fallback to moving averages
            predicted_week = round(daily_average * 7, 2)
            predicted_month = round(daily_average * 30, 2)
            return {
                'next_week': predicted_week,
                'next_month': predicted_month,
                'trend': "Stable (Based on daily averages)"
            }
            
    except Exception as e:
        # Graceful fallback on any computation issue
        print(f"Prediction Model Error: {str(e)}")
        return {
            'next_week': "Calculation busy",
            'next_month': "Calculation busy",
            'trend': "Error calculating trend"
        }
