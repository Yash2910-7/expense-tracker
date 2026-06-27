import numpy as np
from sklearn.ensemble import IsolationForest

def detect_anomaly(new_amount, historical_expenses):
    """
    Evaluates if a new transaction amount is anomalous relative to history.
    Uses IsolationForest for 5+ expenses, falling back to a Z-score statistical check.
    Only flags anomalies representing OVERSPENDING (i.e. above typical values).
    
    Returns:
        bool: True if anomalous, False otherwise.
    """
    try:
        new_val = float(new_amount)
    except (ValueError, TypeError):
        return False
        
    if not historical_expenses or len(historical_expenses) < 4:
        # Not enough data to compute, return False
        return False

    # Extract historical amounts
    amounts = []
    for e in historical_expenses:
        try:
            amt = float(e.amount) if hasattr(e, 'amount') else float(e['amount'])
            amounts.append(amt)
        except (ValueError, TypeError):
            continue
            
    if len(amounts) < 4:
        return False
        
    avg_amount = np.mean(amounts)
    std_amount = np.std(amounts)
    median_amount = np.median(amounts)
    
    # Statistical fallback check if we have between 4 and 6 expenses
    if len(amounts) < 7:
        if std_amount > 1.0:
            threshold = avg_amount + 2.0 * std_amount
            return new_val > threshold
        else:
            return new_val > (avg_amount * 2.5)
            
    # IsolationForest configuration (contamination 10%)
    try:
        X_train = np.array(amounts).reshape(-1, 1)
        model = IsolationForest(contamination=0.10, random_state=42, n_estimators=100)
        model.fit(X_train)
        
        # Predict on new value
        pred = model.predict(np.array([[new_val]]))[0]
        
        # Flag as anomaly only if pred == -1 (anomaly) AND new_val is above the median (overspending)
        if pred == -1 and new_val > median_amount * 1.5:
            return True
    except Exception as e:
        # Fallback to standard statistical check in case of numeric issues
        print(f"Isolation Forest error: {str(e)}")
        if std_amount > 0.0:
            return new_val > (avg_amount + 2.0 * std_amount)
            
    return False
