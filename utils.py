"""
Utility functions for MultiAgent platform
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
import json
import re

# Financial Analysis Helper Functions
def detect_spending_anomalies(expense_df):
    """Detect anomalies in spending patterns using statistical methods"""
    anomalies = []
    
    if expense_df.empty:
        return anomalies
    
    # Group by category and detect outliers
    for category in expense_df['category'].unique():
        category_data = expense_df[expense_df['category'] == category]
        
        if len(category_data) < 3:
            continue
        
        amounts = category_data['amount'].values
        mean_amount = np.mean(amounts)
        std_amount = np.std(amounts)
        
        # Detect outliers (3 standard deviations)
        threshold = mean_amount + 3 * std_amount
        
        outlier_transactions = category_data[category_data['amount'] > threshold]
        
        for _, transaction in outlier_transactions.iterrows():
            anomalies.append({
                'date': transaction['date'].isoformat(),
                'category': category,
                'amount': float(transaction['amount']),
                'expected_range': f"${mean_amount:.2f} ± ${std_amount:.2f}",
                'severity': 'high' if transaction['amount'] > mean_amount + 4 * std_amount else 'medium'
            })
    
    return anomalies

def generate_spending_insights(expense_df):
    """Generate insights from spending patterns"""
    insights = []
    
    if expense_df.empty:
        return insights
    
    # Category insights
    category_spending = expense_df.groupby('category')['amount'].sum()
    total_spending = category_spending.sum()
    
    # Top spending category
    top_category = category_spending.idxmax()
    top_percentage = (category_spending[top_category] / total_spending) * 100
    
    if top_percentage > 40:
        insights.append({
            'type': 'concentration_risk',
            'message': f"{top_percentage:.1f}% of spending is in {top_category}",
            'recommendation': 'Consider diversifying spending categories'
        })
    
    # Spending frequency analysis
    expense_df['date'] = pd.to_datetime(expense_df['date'])
    daily_spending = expense_df.groupby(expense_df['date'].dt.date)['amount'].sum()
    
    # High spending days
    high_spending_threshold = daily_spending.quantile(0.9)
    high_spending_days = daily_spending[daily_spending > high_spending_threshold]
    
    if len(high_spending_days) > 0:
        insights.append({
            'type': 'high_spending_days',
            'message': f"{len(high_spending_days)} days with unusually high spending detected",
            'recommendation': 'Review what causes high spending days and plan accordingly'
        })
    
    return insights

def calculate_income_stability(monthly_income):
    """Calculate income stability metrics"""
    if len(monthly_income) < 3:
        return {'stability_score': 0.5, 'volatility': 0, 'trend': 'insufficient_data'}
    
    # Calculate coefficient of variation
    mean_income = monthly_income.mean()
    std_income = monthly_income.std()
    volatility = (std_income / mean_income) if mean_income > 0 else 0
    
    # Calculate trend
    if len(monthly_income) >= 3:
        x = np.arange(len(monthly_income)).reshape(-1, 1)
        y = monthly_income.values
        model = LinearRegression().fit(x, y)
        trend = 'increasing' if model.coef_[0] > 0 else 'decreasing' if model.coef_[0] < 0 else 'stable'
    else:
        trend = 'stable'
    
    # Stability score (inverse of volatility, normalized to 0-1)
    stability_score = max(0, 1 - volatility)
    
    return {
        'stability_score': float(stability_score),
        'volatility': float(volatility),
        'trend': trend,
        'average_income': float(mean_income),
        'income_range': {
            'min': float(monthly_income.min()),
            'max': float(monthly_income.max())
        }
    }

def detect_income_seasonality(income_df):
    """Detect seasonal patterns in income"""
    if income_df.empty:
        return {'seasonality_detected': False, 'pattern': None}
    
    income_df['date'] = pd.to_datetime(income_df['date'])
    income_df['month'] = income_df['date'].dt.month
    
    monthly_avg = income_df.groupby('month')['amount'].mean()
    
    # Check for significant variation between months
    if len(monthly_avg) < 3:
        return {'seasonality_detected': False, 'pattern': None}
    
    variation_coefficient = monthly_avg.std() / monthly_avg.mean()
    
    if variation_coefficient > 0.3:
        # Find peak months
        peak_months = monthly_avg.nlargest(3).index.tolist()
        low_months = monthly_avg.nsmallest(3).index.tolist()
        
        return {
            'seasonality_detected': True,
            'pattern': {
                'peak_months': peak_months,
                'low_months': low_months,
                'variation_coefficient': float(variation_coefficient)
            }
        }
    
    return {'seasonality_detected': False, 'pattern': None}

def project_income_trends(monthly_income):
    """Project future income based on historical trends"""
    if len(monthly_income) < 3:
        return {'projection': 'insufficient_data'}
    
    # Simple linear regression for projection
    x = np.arange(len(monthly_income)).reshape(-1, 1)
    y = monthly_income.values
    
    model = LinearRegression().fit(x, y)
    
    # Project next 3 months
    future_months = []
    for i in range(1, 4):
        future_x = np.array([[len(monthly_income) + i]])
        predicted_income = model.predict(future_x)[0]
        future_months.append(float(predicted_income))
    
    return {
        'projection': 'available',
        'next_3_months': future_months,
        'trend_slope': float(model.coef_[0]),
        'confidence': 'medium' if len(monthly_income) >= 6 else 'low'
    }

def calculate_income_volatility(income_df):
    """Calculate income volatility coefficient"""
    if income_df.empty:
        return 0
    
    income_df['date'] = pd.to_datetime(income_df['date'])
    monthly_income = income_df.groupby(income_df['date'].dt.to_period('M'))['amount'].sum()
    
    if len(monthly_income) < 2:
        return 0
    
    mean_income = monthly_income.mean()
    std_income = monthly_income.std()
    
    return (std_income / mean_income) if mean_income > 0 else 0

def calculate_health_score(savings_rate, expense_ratio, income_volatility, profile):
    """Calculate overall financial health score (0-100)"""
    score = 50  # Base score
    
    # Savings rate impact (max 25 points)
    if savings_rate >= 0.2:  # 20%+ savings rate
        score += 25
    elif savings_rate >= 0.1:  # 10-20% savings rate
        score += 15
    elif savings_rate >= 0.05:  # 5-10% savings rate
        score += 5
    
    # Expense ratio impact (max 15 points)
    if expense_ratio <= 0.7:  # Living within means
        score += 15
    elif expense_ratio <= 0.85:  # Moderate spending
        score += 10
    elif expense_ratio <= 0.95:  # High spending
        score += 5
    
    # Income volatility impact (max 10 points)
    if income_volatility <= 0.1:  # Very stable income
        score += 10
    elif income_volatility <= 0.2:  # Moderately stable
        score += 7
    elif income_volatility <= 0.3:  # Some volatility
        score += 3
    
    # Employment type adjustment
    if profile and profile.employment_type in ['gig', 'informal']:
        score -= 10  # Penalty for irregular income types
    
    return max(0, min(100, score))

def identify_risk_factors(savings_rate, expense_ratio, income_volatility):
    """Identify specific financial risk factors"""
    risks = []
    
    if savings_rate < 0.05:
        risks.append({
            'factor': 'low_savings',
            'severity': 'high',
            'description': 'Savings rate below 5%'
        })
    
    if expense_ratio > 0.95:
        risks.append({
            'factor': 'high_expenses',
            'severity': 'high',
            'description': 'Expenses exceed 95% of income'
        })
    
    if income_volatility > 0.4:
        risks.append({
            'factor': 'high_volatility',
            'severity': 'medium',
            'description': 'High income volatility detected'
        })
    
    return risks

def predict_time_series(series):
    """Simple time series prediction using linear regression"""
    if len(series) < 3:
        return {'error': 'Insufficient data for prediction'}
    
    x = np.arange(len(series)).reshape(-1, 1)
    y = series.values
    
    model = LinearRegression().fit(x, y)
    
    # Predict next 3 periods
    predictions = []
    for i in range(1, 4):
        future_x = np.array([[len(series) + i]])
        pred = model.predict(future_x)[0]
        predictions.append(float(pred))
    
    return {
        'predictions': predictions,
        'trend': 'increasing' if model.coef_[0] > 0 else 'decreasing',
        'r_squared': float(model.score(x, y))
    }

def calculate_overall_risk(risks):
    """Calculate overall financial risk level"""
    if not risks:
        return 'low'
    
    high_risk_count = sum(1 for r in risks if r.get('severity') == 'high')
    medium_risk_count = sum(1 for r in risks if r.get('severity') == 'medium')
    
    if high_risk_count >= 2:
        return 'very_high'
    elif high_risk_count >= 1:
        return 'high'
    elif medium_risk_count >= 2:
        return 'medium'
    elif medium_risk_count >= 1:
        return 'low-medium'
    else:
        return 'low'

def generate_risk_mitigation_plan(risks):
    """Generate risk mitigation strategies"""
    strategies = []
    
    for risk in risks:
        if risk['type'] == 'income_volatility':
            strategies.append({
                'risk': risk['type'],
                'strategy': 'Build emergency fund covering 6-12 months of expenses',
                'timeline': '6-12 months',
                'priority': 'high'
            })
        elif risk['type'] == 'overspending':
            strategies.append({
                'risk': risk['type'],
                'strategy': 'Create and follow a strict budget, reduce non-essential expenses',
                'timeline': '1-3 months',
                'priority': 'high'
            })
        elif risk['type'] == 'emergency_fund':
            strategies.append({
                'risk': risk['type'],
                'strategy': 'Automate savings to build emergency fund gradually',
                'timeline': '12-18 months',
                'priority': 'medium'
            })
    
    return strategies

# Goal Management Functions
def analyze_goal_progress(transactions):
    """Analyze progress towards financial goals"""
    goals_analysis = {
        'emergency_fund': check_emergency_fund_progress(transactions),
        'savings_goals': check_savings_goals(transactions),
        'debt_reduction': check_debt_reduction_progress(transactions),
        'investment_goals': check_investment_progress(transactions)
    }
    
    return goals_analysis

def check_emergency_fund_progress(transactions):
    """Check progress on emergency fund goals"""
    # Calculate monthly expenses from transaction data
    expense_transactions = [t for t in transactions if t.transaction_type == 'expense']
    
    if not expense_transactions:
        return {'status': 'no_data', 'target_months': 6}
    
    # Calculate average monthly expenses
    total_expenses = sum(t.amount for t in expense_transactions)
    
    # Calculate current savings (income - expenses)
    income_transactions = [t for t in transactions if t.transaction_type == 'income']
    total_income = sum(t.amount for t in income_transactions)
    current_savings = total_income - total_expenses
    
    # Target emergency fund (6 months of expenses)
    monthly_expenses = total_expenses / max(1, len(set(t.date.month for t in expense_transactions)))
    target_fund = monthly_expenses * 6
    
    progress_percentage = (current_savings / target_fund) * 100 if target_fund > 0 else 0
    
    return {
        'status': 'on_track' if progress_percentage >= 100 else 'in_progress',
        'current_savings': float(current_savings),
        'target_amount': float(target_fund),
        'progress_percentage': float(progress_percentage),
        'months_covered': int(current_savings / monthly_expenses) if monthly_expenses > 0 else 0
    }

def check_savings_goals(transactions):
    """Check progress on savings goals"""
    income_transactions = [t for t in transactions if t.transaction_type == 'income']
    expense_transactions = [t for t in transactions if t.transaction_type == 'expense']
    
    total_income = sum(t.amount for t in income_transactions)
    total_expenses = sum(t.amount for t in expense_transactions)
    
    savings_rate = (total_income - total_expenses) / total_income if total_income > 0 else 0
    
    return {
        'savings_rate': float(savings_rate),
        'total_saved': float(total_income - total_expenses),
        'recommendation': 'Aim for 20% savings rate for optimal financial health'
    }

def check_debt_reduction_progress(transactions):
    """Check progress on debt reduction"""
    debt_transactions = [t for t in transactions if t.category.lower() in ['debt', 'loan', 'credit card']]
    
    if not debt_transactions:
        return {'status': 'no_debt_detected'}
    
    total_debt_payments = sum(t.amount for t in debt_transactions)
    
    return {
        'total_debt_payments': float(total_debt_payments),
        'payment_frequency': len(debt_transactions),
        'recommendation': 'Consider increasing debt payments to save on interest'
    }

def check_investment_progress(transactions):
    """Check progress on investment goals"""
    investment_transactions = [t for t in transactions if t.category.lower() in ['investment', 'stocks', 'retirement']]
    
    if not investment_transactions:
        return {'status': 'no_investments_detected'}
    
    total_invested = sum(t.amount for t in investment_transactions)
    
    return {
        'total_invested': float(total_invested),
        'investment_frequency': len(investment_transactions),
        'recommendation': 'Consider regular investment contributions for long-term growth'
    }

# AI Helper Functions
def prepare_recommendation_context(df, profile):
    """Prepare context for AI recommendations"""
    context = {
        'financial_summary': {
            'total_income': float(df[df['type'] == 'income']['amount'].sum()) if not df[df['type'] == 'income'].empty else 0,
            'total_expenses': float(df[df['type'] == 'expense']['amount'].sum()) if not df[df['type'] == 'expense'].empty else 0,
            'transaction_count': len(df),
            'categories': df['category'].unique().tolist() if not df.empty else []
        },
        'user_profile': {
            'employment_type': profile.employment_type if profile else 'unknown',
            'monthly_income': profile.monthly_income if profile else 0,
            'monthly_expenses': profile.monthly_expenses if profile else 0
        }
    }
    
    return json.dumps(context, indent=2)

def parse_ai_recommendations(ai_response):
    """Parse AI-generated recommendations"""
    try:
        # Try to parse as JSON
        recommendations = json.loads(ai_response)
        return recommendations
    except json.JSONDecodeError:
        # Fallback: extract recommendations using regex
        recommendations = []
        
        # Look for recommendation patterns
        pattern = r'(?:recommendation|advice|suggestion)[:\s]*([^.!?]*[.!?])'
        matches = re.findall(pattern, ai_response, re.IGNORECASE)
        
        for match in matches:
            recommendations.append({
                'category': 'general',
                'priority': 'medium',
                'action': match.strip(),
                'impact': 'positive',
                'timeline': 'immediate'
            })
        
        return recommendations

def generate_fallback_recommendations(df, profile):
    """Generate rule-based recommendations as fallback"""
    recommendations = []
    
    income_df = df[df['type'] == 'income']
    expense_df = df[df['type'] == 'expense']
    
    total_income = income_df['amount'].sum() if not income_df.empty else 0
    total_expenses = expense_df['amount'].sum() if not expense_df.empty else 0
    
    savings_rate = (total_income - total_expenses) / total_income if total_income > 0 else 0
    
    if savings_rate < 0.1:
        recommendations.append({
            'category': 'savings',
            'priority': 'high',
            'action': 'Increase savings rate to at least 10% of income',
            'impact': 'Build financial security and emergency fund',
            'timeline': '1-3 months'
        })
    
    if profile and profile.employment_type in ['gig', 'informal']:
        recommendations.append({
            'category': 'emergency_fund',
            'priority': 'high',
            'action': 'Build emergency fund covering 6-12 months of expenses',
            'impact': 'Protect against income volatility',
            'timeline': '6-12 months'
        })
    
    return recommendations

# Agent Collaboration Functions
def execute_sequential_collaboration(agents, task_data, user_id):
    """Execute agents in sequence"""
    results = []
    current_data = task_data
    
    for agent_type in agents:
        # Get agent
        from agents import AgentManager
        agent_manager = AgentManager()
        agent = agent_manager.get_agent(agent_type)
        
        if not agent:
            return {'error': f'Agent {agent_type} not found'}
        
        # Process task
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(agent.process_task(current_data))
        
        results.append({
            'agent': agent_type,
            'result': result,
            'success': result.get('success', False)
        })
        
        # Pass result to next agent
        current_data = result
    
    return {
        'collaboration_type': 'sequential',
        'agents': agents,
        'results': results,
        'success': all(r['success'] for r in results)
    }

def execute_parallel_collaboration(agents, task_data, user_id):
    """Execute agents in parallel"""
    from agents import AgentManager
    agent_manager = AgentManager()
    
    # Get all agents
    agent_tasks = []
    for agent_type in agents:
        agent = agent_manager.get_agent(agent_type)
        if agent:
            agent_tasks.append((agent_type, agent))
    
    # Execute tasks in parallel
    import asyncio
    async def run_parallel():
        tasks = []
        for agent_type, agent in agent_tasks:
            task = asyncio.create_task(agent.process_task(task_data))
            tasks.append((agent_type, task))
        
        results = []
        for agent_type, task in tasks:
            result = await task
            results.append({
                'agent': agent_type,
                'result': result,
                'success': result.get('success', False)
            })
        
        return results
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(run_parallel())
    
    return {
        'collaboration_type': 'parallel',
        'agents': agents,
        'results': results,
        'success': any(r['success'] for r in results)
    }
