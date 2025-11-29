from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import io
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import json
from agents import AgentManager
from utils import (
    detect_spending_anomalies, generate_spending_insights,
    calculate_income_stability, detect_income_seasonality,
    project_income_trends, calculate_income_volatility,
    calculate_health_score, identify_risk_factors,
    predict_time_series, calculate_overall_risk,
    generate_risk_mitigation_plan, analyze_goal_progress,
    prepare_recommendation_context, parse_ai_recommendations,
    generate_fallback_recommendations
)
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest

load_dotenv()

app = Flask(__name__)

# Load configuration
from config import get_config
config = get_config()
app.config.from_object(config)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_EXTENSIONS'] = {'.csv', '.xlsx', '.xls'}
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Disable CSRF for JWT

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app, supports_credentials=True)

# Configure OpenAI API (PipeShift)
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_BASE_URL', 'https://api.pipeshift.com/api/v0/')
)
AI_MODEL = os.getenv('OPENAI_MODEL', 'neysa-qwen3-vl-30b-a3b')

# Initialize Agent Manager
agent_manager = AgentManager()

# Plaid Configuration
PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET')
PLAID_ENV = os.getenv('PLAID_ENV', 'sandbox')

# Map environment to Plaid host
plaid_env_map = {
    'sandbox': plaid.Environment.Sandbox,
    'development': plaid.Environment.Development,
    'production': plaid.Environment.Production
}

# Handle if Development doesn't exist in this Plaid version
if not hasattr(plaid.Environment, 'Development'):
    plaid_env_map['development'] = plaid.Environment.Sandbox

configuration = plaid.Configuration(
    host=plaid_env_map.get(PLAID_ENV, plaid.Environment.Sandbox),
    api_key={
        'clientId': PLAID_CLIENT_ID,
        'secret': PLAID_SECRET,
    }
)

api_client = plaid.ApiClient(configuration)
plaid_client = plaid_api.PlaidApi(api_client)

# JWT Error Handlers
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    print(f"JWT EXPIRED: {jwt_payload}")
    return jsonify({'error': 'Token has expired'}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    print(f"JWT INVALID: {error}")
    return jsonify({'error': 'Invalid token'}), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    print(f"JWT MISSING: {error}")
    return jsonify({'error': 'Authorization token is required'}), 401

# Serve static files
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/test')
def test():
    """Test endpoint - no auth required"""
    return jsonify({'status': 'ok', 'message': 'API is working'})

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile = db.relationship('UserProfile', backref='user', uselist=False)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    employment_type = db.Column(db.String(50))  # 'gig', 'informal', 'formal'
    monthly_income_range = db.Column(db.String(20))
    financial_goals = db.Column(db.Text)
    risk_tolerance = db.Column(db.String(20))  # 'low', 'medium', 'high'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    transaction_type = db.Column(db.String(20), nullable=False)  # 'income', 'expense'
    date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FinancialInsight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    insight_type = db.Column(db.String(50), nullable=False)  # 'spending_pattern', 'income_alert', 'recommendation'
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='medium')  # 'low', 'medium', 'high'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    agent_type = db.Column(db.String(50), nullable=False)  # 'financial', 'research', 'productivity', 'learning'
    task_type = db.Column(db.String(50), nullable=False)  # Specific task type within agent
    priority = db.Column(db.String(20), default='medium')  # 'low', 'medium', 'high'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'in_progress', 'completed', 'failed'
    task_data = db.Column(db.Text)  # JSON string of task data
    result = db.Column(db.Text)  # JSON string of task result
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships for agent coordination
    parent_task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    child_tasks = db.relationship('Task', backref=db.backref('parent_task', remote_side=[id]), lazy='dynamic')

class AgentWorkflow(db.Model):
    """Track agent workflows and coordination"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    workflow_name = db.Column(db.String(100), nullable=False)
    agent_sequence = db.Column(db.Text)  # JSON array of agent types in order
    current_step = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='active')  # 'active', 'completed', 'failed'
    task_ids = db.Column(db.Text)  # JSON array of task IDs in this workflow
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PlaidAccount(db.Model):
    """Store Plaid connected bank accounts"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    access_token = db.Column(db.String(200), nullable=False)  # Encrypt in production!
    item_id = db.Column(db.String(100), nullable=False)
    institution_name = db.Column(db.String(100))
    institution_id = db.Column(db.String(100))
    account_name = db.Column(db.String(100))
    account_type = db.Column(db.String(50))
    last_synced = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    user = User(
        email=data['email'],
        password=data['password'],  # In production, hash this password
        name=data['name']
    )
    db.session.add(user)
    db.session.commit()
    
    # Create user profile
    profile = UserProfile(user_id=user.id)
    db.session.add(profile)
    db.session.commit()
    
    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name
        }
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    
    if user and user.password == data['password']:  # In production, verify hashed password
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            'access_token': access_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name
            }
        })
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

def get_current_user_id():
    """Helper to get user ID as integer from JWT"""
    return int(get_jwt_identity())

def categorize_transaction(description, amount, transaction_type):
    """Smart transaction categorization with keyword matching and AI fallback"""
    desc_lower = description.lower()
    
    # Income categories
    if transaction_type == 'income':
        if any(word in desc_lower for word in ['salary', 'payroll', 'wage', 'pay']):
            return 'Salary'
        elif any(word in desc_lower for word in ['freelance', 'consulting', 'contract', 'gig']):
            return 'Freelance'
        elif any(word in desc_lower for word in ['dividend', 'interest', 'investment', 'stock']):
            return 'Investment'
        elif any(word in desc_lower for word in ['bonus', 'commission', 'tip']):
            return 'Bonus'
        elif any(word in desc_lower for word in ['refund', 'reimbursement']):
            return 'Refund'
        else:
            return 'Other Income'
    
    # Expense categories - Housing
    if any(word in desc_lower for word in ['rent', 'mortgage', 'property', 'lease']):
        return 'Housing'
    
    # Utilities
    if any(word in desc_lower for word in ['electric', 'electricity', 'pg&e', 'pge', 'power', 'water', 'gas bill', 'utility']):
        return 'Utilities'
    if any(word in desc_lower for word in ['internet', 'comcast', 'xfinity', 'wifi', 'broadband']):
        return 'Utilities'
    if any(word in desc_lower for word in ['phone', 'mobile', 'verizon', 'at&t', 'tmobile', 't-mobile', 'cellular']):
        return 'Utilities'
    
    # Transportation
    if any(word in desc_lower for word in ['gas', 'fuel', 'shell', 'chevron', '76', 'exxon', 'mobil', 'bp', 'arco', 'petrol']):
        return 'Transportation'
    if any(word in desc_lower for word in ['uber', 'lyft', 'taxi', 'cab', 'ride']):
        return 'Transportation'
    if any(word in desc_lower for word in ['parking', 'toll', 'metro', 'transit', 'bus', 'train']):
        return 'Transportation'
    if any(word in desc_lower for word in ['car insurance', 'auto insurance', 'geico', 'progressive', 'state farm']):
        return 'Transportation'
    if any(word in desc_lower for word in ['car wash', 'oil change', 'mechanic', 'repair', 'maintenance', 'tire']):
        return 'Transportation'
    
    # Food & Dining
    if any(word in desc_lower for word in ['grocery', 'groceries', 'supermarket', 'safeway', 'whole foods', 'trader joe', 'costco', 'walmart', 'target']):
        return 'Groceries'
    if any(word in desc_lower for word in ['restaurant', 'cafe', 'coffee', 'starbucks', 'dunkin', 'mcdonald', 'burger', 'pizza', 'chipotle', 'subway', 'taco', 'dining', 'food', 'lunch', 'dinner', 'breakfast']):
        return 'Dining'
    
    # Entertainment & Subscriptions
    if any(word in desc_lower for word in ['netflix', 'hulu', 'disney', 'spotify', 'apple music', 'youtube premium', 'amazon prime', 'subscription', 'streaming']):
        return 'Entertainment'
    if any(word in desc_lower for word in ['gym', 'fitness', 'yoga', 'la fitness', 'planet fitness', 'workout']):
        return 'Entertainment'
    if any(word in desc_lower for word in ['movie', 'cinema', 'theater', 'amc', 'concert', 'show', 'ticket']):
        return 'Entertainment'
    if any(word in desc_lower for word in ['game', 'gaming', 'steam', 'playstation', 'xbox', 'nintendo']):
        return 'Entertainment'
    
    # Shopping
    if any(word in desc_lower for word in ['amazon', 'ebay', 'etsy', 'shopping', 'purchase']):
        return 'Shopping'
    if any(word in desc_lower for word in ['clothing', 'clothes', 'fashion', 'nordstrom', 'macy', 'gap', 'zara', 'h&m']):
        return 'Shopping'
    if any(word in desc_lower for word in ['electronics', 'best buy', 'apple store', 'computer', 'phone']):
        return 'Shopping'
    if any(word in desc_lower for word in ['home depot', 'lowes', 'hardware', 'furniture', 'ikea']):
        return 'Shopping'
    
    # Healthcare
    if any(word in desc_lower for word in ['health insurance', 'medical', 'doctor', 'hospital', 'clinic', 'pharmacy', 'cvs', 'walgreens', 'prescription', 'medicine']):
        return 'Healthcare'
    if any(word in desc_lower for word in ['dental', 'dentist', 'orthodont']):
        return 'Healthcare'
    if any(word in desc_lower for word in ['vet', 'veterinary', 'animal hospital', 'pet clinic']):
        return 'Pet Care'
    
    # Personal Care
    if any(word in desc_lower for word in ['haircut', 'salon', 'barber', 'spa', 'beauty', 'cosmetic']):
        return 'Personal Care'
    
    # Education
    if any(word in desc_lower for word in ['school', 'tuition', 'education', 'course', 'udemy', 'coursera', 'book', 'textbook']):
        return 'Education'
    
    # Gifts & Donations
    if any(word in desc_lower for word in ['gift', 'present', 'donation', 'charity']):
        return 'Gifts'
    
    # Insurance (non-auto)
    if any(word in desc_lower for word in ['insurance']) and 'auto' not in desc_lower and 'car' not in desc_lower:
        return 'Insurance'
    
    # Default: Use AI for unclear cases
    try:
        cat_prompt = f"""Categorize this transaction into ONE of these categories:
Housing, Utilities, Transportation, Groceries, Dining, Entertainment, Shopping, Healthcare, Pet Care, Personal Care, Education, Gifts, Insurance, Other

Transaction: {description}
Amount: ${amount}

Return ONLY the category name, nothing else."""
        
        cat_response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "Return only the category name from the provided list."},
                {"role": "user", "content": cat_prompt}
            ],
            max_tokens=20,
            temperature=0.1
        )
        category = cat_response.choices[0].message.content.strip()
        
        # Validate it's one of our categories
        valid_categories = ['Housing', 'Utilities', 'Transportation', 'Groceries', 'Dining', 'Entertainment', 
                          'Shopping', 'Healthcare', 'Pet Care', 'Personal Care', 'Education', 'Gifts', 'Insurance']
        if category in valid_categories:
            return category
    except:
        pass
    
    return 'Other'

def generate_insights_for_user(user_id):
    """Generate AI-powered financial insights for a user"""
    try:
        # Get user's transactions
        transactions = Transaction.query.filter_by(user_id=user_id).all()
        
        if not transactions or len(transactions) < 3:
            # Create a welcome insight
            insight = FinancialInsight(
                user_id=user_id,
                insight_type='welcome',
                content='Welcome! Start adding transactions to get personalized AI insights about your spending patterns, savings opportunities, and financial health.',
                priority='low'
            )
            db.session.add(insight)
            db.session.commit()
            return
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'amount': t.amount,
            'category': t.category,
            'type': t.transaction_type,
            'date': t.date
        } for t in transactions])
        
        # Separate income and expenses
        expenses = df[df['type'] == 'expense']
        income = df[df['type'] == 'income']
        
        insights_to_create = []
        
        # 1. Spending pattern insights
        if not expenses.empty:
            category_spending = expenses.groupby('category')['amount'].sum().sort_values(ascending=False)
            total_expenses = category_spending.sum()
            
            # Top spending category
            if len(category_spending) > 0:
                top_category = category_spending.index[0]
                top_amount = category_spending.iloc[0]
                top_percentage = (top_amount / total_expenses) * 100
                
                if top_percentage > 30:
                    insights_to_create.append({
                        'insight_type': 'spending_pattern',
                        'content': f'Your {top_category} spending accounts for {top_percentage:.1f}% (${top_amount:.2f}) of total expenses. Consider reviewing this category for potential savings.',
                        'priority': 'high' if top_percentage > 50 else 'medium'
                    })
        
        # 2. Income vs Expenses
        if not income.empty and not expenses.empty:
            total_income = income['amount'].sum()
            total_expenses_val = expenses['amount'].sum()
            savings_rate = ((total_income - total_expenses_val) / total_income * 100) if total_income > 0 else 0
            
            if savings_rate < 10:
                insights_to_create.append({
                    'insight_type': 'savings_alert',
                    'content': f'Your savings rate is {savings_rate:.1f}%. Financial experts recommend saving at least 20% of your income. Try to reduce expenses or increase income.',
                    'priority': 'high'
                })
            elif savings_rate >= 20:
                insights_to_create.append({
                    'insight_type': 'savings_success',
                    'content': f'Great job! You\'re saving {savings_rate:.1f}% of your income. Keep up the excellent financial discipline!',
                    'priority': 'low'
                })
        
        # 3. Recent spending trends
        if not expenses.empty:
            expenses['date'] = pd.to_datetime(expenses['date'])
            expenses = expenses.sort_values('date')
            
            # Last 30 days vs previous 30 days
            recent_date = expenses['date'].max()
            last_30_days = expenses[expenses['date'] >= (recent_date - pd.Timedelta(days=30))]
            prev_30_days = expenses[(expenses['date'] >= (recent_date - pd.Timedelta(days=60))) & 
                                   (expenses['date'] < (recent_date - pd.Timedelta(days=30)))]
            
            if not last_30_days.empty and not prev_30_days.empty:
                recent_spending = last_30_days['amount'].sum()
                previous_spending = prev_30_days['amount'].sum()
                change_pct = ((recent_spending - previous_spending) / previous_spending * 100) if previous_spending > 0 else 0
                
                if abs(change_pct) > 20:
                    direction = 'increased' if change_pct > 0 else 'decreased'
                    insights_to_create.append({
                        'insight_type': 'trend_alert',
                        'content': f'Your spending has {direction} by {abs(change_pct):.1f}% in the last 30 days compared to the previous period. Review your recent transactions to understand this change.',
                        'priority': 'medium'
                    })
        
        # 4. Unusual transactions
        if not expenses.empty and len(expenses) > 10:
            mean_expense = expenses['amount'].mean()
            std_expense = expenses['amount'].std()
            unusual_threshold = mean_expense + (2 * std_expense)
            
            unusual_transactions = expenses[expenses['amount'] > unusual_threshold]
            if len(unusual_transactions) > 0:
                insights_to_create.append({
                    'insight_type': 'anomaly_detection',
                    'content': f'Detected {len(unusual_transactions)} unusually large transaction(s). Largest: ${unusual_transactions["amount"].max():.2f} in {unusual_transactions.iloc[unusual_transactions["amount"].argmax()]["category"]}.',
                    'priority': 'medium'
                })
        
        # 5. Category recommendations
        if not expenses.empty:
            # Find categories with high spending
            avg_by_category = expenses.groupby('category')['amount'].mean()
            for category, avg_amount in avg_by_category.items():
                if avg_amount > 100 and category.lower() in ['shopping', 'entertainment', 'dining']:
                    insights_to_create.append({
                        'insight_type': 'recommendation',
                        'content': f'Your average {category} transaction is ${avg_amount:.2f}. Consider setting a budget limit for this category to control spending.',
                        'priority': 'low'
                    })
                    break  # Only add one recommendation
        
        # Save insights to database
        for insight_data in insights_to_create[:5]:  # Limit to 5 insights
            insight = FinancialInsight(
                user_id=user_id,
                insight_type=insight_data['insight_type'],
                content=insight_data['content'],
                priority=insight_data['priority']
            )
            db.session.add(insight)
        
        db.session.commit()
        print(f"Generated {len(insights_to_create)} insights for user {user_id}")
        
    except Exception as e:
        print(f"Error generating insights: {e}")
        db.session.rollback()

@app.route('/api/profile', methods=['GET', 'PUT'])
@jwt_required()
def user_profile():
    user_id = get_current_user_id()
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    
    if request.method == 'GET':
        return jsonify({
            'employment_type': profile.employment_type,
            'monthly_income_range': profile.monthly_income_range,
            'financial_goals': profile.financial_goals,
            'risk_tolerance': profile.risk_tolerance
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        profile.employment_type = data.get('employment_type', profile.employment_type)
        profile.monthly_income_range = data.get('monthly_income_range', profile.monthly_income_range)
        profile.financial_goals = data.get('financial_goals', profile.financial_goals)
        profile.risk_tolerance = data.get('risk_tolerance', profile.risk_tolerance)
        profile.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'})

@app.route('/api/transactions', methods=['GET', 'POST'])
@jwt_required()
def transactions():
    user_id = get_current_user_id()
    
    if request.method == 'GET':
        transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).all()
        return jsonify([{
            'id': t.id,
            'amount': t.amount,
            'category': t.category,
            'description': t.description,
            'transaction_type': t.transaction_type,
            'date': t.date.isoformat()
        } for t in transactions])
    
    elif request.method == 'POST':
        data = request.get_json()
        transaction = Transaction(
            user_id=user_id,
            amount=data['amount'],
            category=data['category'],
            description=data.get('description', ''),
            transaction_type=data['transaction_type'],
            date=datetime.fromisoformat(data['date'])
        )
        db.session.add(transaction)
        db.session.commit()
        
        # Trigger analysis for new transaction
        analyze_transaction_patterns(user_id, transaction)
        
        return jsonify({'message': 'Transaction added successfully', 'id': transaction.id}), 201

@app.route('/api/insights', methods=['GET'])
@jwt_required()
def get_insights():
    user_id = get_current_user_id()
    
    # Auto-generate insights if none exist
    existing_insights = FinancialInsight.query.filter_by(user_id=user_id).count()
    if existing_insights == 0:
        try:
            generate_insights_for_user(user_id)
        except Exception as e:
            print(f"Error generating insights: {e}")
    
    insights = FinancialInsight.query.filter_by(user_id=user_id).order_by(FinancialInsight.created_at.desc()).limit(20).all()
    return jsonify([{
        'id': i.id,
        'insight_type': i.insight_type,
        'content': i.content,
        'priority': i.priority,
        'created_at': i.created_at.isoformat(),
        'is_read': i.is_read
    } for i in insights])

@app.route('/api/analysis/spending-patterns', methods=['GET'])
@jwt_required()
def spending_patterns():
    user_id = get_current_user_id()
    transactions = Transaction.query.filter_by(user_id=user_id, transaction_type='expense').all()
    
    if not transactions:
        return jsonify({
            'category_spending': {},
            'monthly_trends': {},
            'total_expenses': 0,
            'average_monthly': 0
        })
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame([{
        'amount': t.amount,
        'category': t.category,
        'date': t.date
    } for t in transactions])
    
    # Category-wise spending
    category_spending = df.groupby('category')['amount'].sum().to_dict()
    
    # Monthly trends
    df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
    monthly_spending = df.groupby('month')['amount'].sum().to_dict()
    
    return jsonify({
        'category_spending': {str(k): float(v) for k, v in category_spending.items()},
        'monthly_trends': {str(k): float(v) for k, v in monthly_spending.items()},
        'total_expenses': float(df['amount'].sum()),
        'average_monthly': float(df.groupby('month')['amount'].sum().mean()) if len(df) > 0 else 0
    })

@app.route('/api/analysis/income-variability', methods=['GET'])
@jwt_required()
def income_variability():
    user_id = get_current_user_id()
    transactions = Transaction.query.filter_by(user_id=user_id, transaction_type='income').all()
    
    if not transactions:
        return jsonify({
            'monthly_income': {},
            'average_income': 0,
            'total_income': 0,
            'variability': 0,
            'stability_score': 1.0
        })
    
    df = pd.DataFrame([{
        'amount': t.amount,
        'date': t.date
    } for t in transactions])
    
    df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
    monthly_income = df.groupby('month')['amount'].sum()
    
    # Calculate variability metrics
    income_std = float(monthly_income.std()) if len(monthly_income) > 1 else 0
    income_mean = float(monthly_income.mean())
    variability_score = income_std / income_mean if income_mean > 0 else 0
    
    return jsonify({
        'variability_score': variability_score,
        'variability': variability_score,
        'monthly_income': {str(k): float(v) for k, v in monthly_income.to_dict().items()},
        'average_income': income_mean,
        'total_income': float(df['amount'].sum()),
        'income_stability': 'stable' if variability_score < 0.2 else 'moderate' if variability_score < 0.5 else 'highly_variable'
    })

@app.route('/api/coach/advice', methods=['POST'])
@jwt_required()
def get_financial_advice():
    user_id = get_current_user_id()
    data = request.get_json()
    user_context = data.get('context', '')
    
    # Get user's financial data
    user = User.query.get(user_id)
    profile = user.profile
    recent_transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).limit(20).all()
    
    # Prepare context for Gemini
    financial_summary = prepare_financial_summary(user, profile, recent_transactions)
    
    prompt = f"""
    As an expert financial coach specializing in gig workers and informal sector employees, 
    provide personalized advice based on the following financial data:
    
    User Profile: {financial_summary}
    Specific Context: {user_context}
    
    Consider:
    1. Income variability and irregular cash flow
    2. Emergency fund needs for unstable income
    3. Debt management strategies
    4. Savings automation for irregular income
    5. Investment options for risk tolerance level: {profile.risk_tolerance}
    
    Provide actionable, specific advice in 3-5 bullet points. Be encouraging and practical.
    """
    
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert financial coach."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return jsonify({'advice': response.choices[0].message.content})
    except Exception as e:
        return jsonify({'error': 'Failed to generate advice', 'details': str(e)}), 500

def prepare_financial_summary(user, profile, transactions):
    """Prepare a summary of user's financial situation for AI analysis"""
    income_transactions = [t for t in transactions if t.transaction_type == 'income']
    expense_transactions = [t for t in transactions if t.transaction_type == 'expense']
    
    total_income = sum(t.amount for t in income_transactions)
    total_expenses = sum(t.amount for t in expense_transactions)
    
    return f"""
    Name: {user.name}
    Employment Type: {profile.employment_type}
    Monthly Income Range: {profile.monthly_income_range}
    Risk Tolerance: {profile.risk_tolerance}
    Financial Goals: {profile.financial_goals}
    Recent Income: {total_income}
    Recent Expenses: {total_expenses}
    Net Income: {total_income - total_expenses}
    """

def analyze_transaction_patterns(user_id, transaction):
    """Analyze transaction patterns and generate insights"""
    try:
        # Get recent transactions for pattern analysis
        recent_transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).limit(30).all()
        
        if len(recent_transactions) < 5:
            return  # Not enough data for analysis
        
        # Analyze spending patterns
        if transaction.transaction_type == 'expense':
            analyze_spending_spike(user_id, transaction, recent_transactions)
        
        # Analyze income patterns for gig workers
        if transaction.transaction_type == 'income':
            analyze_income_pattern(user_id, transaction, recent_transactions)
            
    except Exception as e:
        print(f"Error in pattern analysis: {e}")

def analyze_spending_spike(user_id, new_transaction, recent_transactions):
    """Detect unusual spending spikes"""
    category_transactions = [t for t in recent_transactions if t.category == new_transaction.category and t.transaction_type == 'expense']
    
    if len(category_transactions) < 3:
        return
    
    amounts = [t.amount for t in category_transactions]
    avg_amount = np.mean(amounts)
    std_amount = np.std(amounts)
    
    # Check if new transaction is significantly higher than average
    if new_transaction.amount > avg_amount + 2 * std_amount:
        insight = FinancialInsight(
            user_id=user_id,
            insight_type='spending_pattern',
            content=f"Unusual spending detected in {new_transaction.category}: ${new_transaction.amount:.2f} is significantly higher than your average of ${avg_amount:.2f}",
            priority='high'
        )
        db.session.add(insight)
        db.session.commit()

def analyze_income_pattern(user_id, new_transaction, recent_transactions):
    """Analyze income patterns for gig workers"""
    income_transactions = [t for t in recent_transactions if t.transaction_type == 'income']
    
    if len(income_transactions) < 3:
        return
    
    # Check for income gaps
    sorted_dates = sorted([t.date for t in income_transactions])
    gaps = []
    for i in range(1, len(sorted_dates)):
        gap = (sorted_dates[i] - sorted_dates[i-1]).days
        gaps.append(gap)
    
    avg_gap = np.mean(gaps)
    
    if avg_gap > 14:  # More than 2 weeks between income on average
        insight = FinancialInsight(
            user_id=user_id,
            insight_type='income_alert',
            content=f"Irregular income pattern detected: Average gap of {avg_gap:.1f} days between income sources. Consider building a larger emergency fund.",
            priority='medium'
        )
        db.session.add(insight)
        db.session.commit()

# Multi-Agent Routes
@app.route('/api/agents', methods=['GET'])
@jwt_required()
def get_agents():
    """Get all available agents and their capabilities"""
    return jsonify(agent_manager.get_agent_capabilities())

@app.route('/api/agents/performance', methods=['GET'])
@jwt_required()
def get_agent_performance():
    """Get performance metrics for all agents"""
    return jsonify(agent_manager.get_agent_performance())

@app.route('/api/tasks', methods=['GET', 'POST'])
@jwt_required()
def manage_tasks():
    """Get user tasks or create new task"""
    user_id = get_current_user_id()
    
    if request.method == 'GET':
        tasks = Task.query.filter_by(user_id=user_id).order_by(Task.created_at.desc()).all()
        return jsonify([{
            'id': t.id,
            'title': t.title,
            'description': t.description,
            'agent_type': t.agent_type,
            'task_type': t.task_type,
            'priority': t.priority,
            'status': t.status,
            'result': json.loads(t.result) if t.result else None,
            'created_at': t.created_at.isoformat(),
            'completed_at': t.completed_at.isoformat() if t.completed_at else None
        } for t in tasks])
    
    elif request.method == 'POST':
        data = request.get_json()
        
        # Create task record
        task = Task(
            user_id=user_id,
            title=data['title'],
            description=data.get('description', ''),
            agent_type=data['agent_type'],
            task_type=data.get('task_type', 'general'),
            priority=data.get('priority', 'medium'),
            task_data=json.dumps(data.get('task_data', {}))
        )
        db.session.add(task)
        db.session.commit()
        
        # Route task to appropriate agent
        task_data = {
            'agent_type': data['agent_type'],
            'task_type': data.get('task_type', 'general'),
            **data.get('task_data', {})
        }
        
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(agent_manager.route_task(task_data))
            
            # Update task with result
            task.status = 'completed' if result['success'] else 'failed'
            task.result = json.dumps(result)
            task.completed_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'message': 'Task completed',
                'task_id': task.id,
                'result': result
            })
            
        except Exception as e:
            task.status = 'failed'
            task.result = json.dumps({'error': str(e)})
            db.session.commit()
            
            return jsonify({'error': 'Task processing failed', 'details': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def manage_task(task_id):
    """Get, update, or delete specific task"""
    user_id = get_current_user_id()
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    if request.method == 'GET':
        return jsonify({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'agent_type': task.agent_type,
            'task_type': task.task_type,
            'priority': task.priority,
            'status': task.status,
            'task_data': json.loads(task.task_data) if task.task_data else {},
            'result': json.loads(task.result) if task.result else None,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat(),
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        task.title = data.get('title', task.title)
        task.description = data.get('description', task.description)
        task.priority = data.get('priority', task.priority)
        task.status = data.get('status', task.status)
        task.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Task updated successfully'})
    
    elif request.method == 'DELETE':
        db.session.delete(task)
        db.session.commit()
        return jsonify({'message': 'Task deleted successfully'})

@app.route('/api/tasks/<int:task_id>/rerun', methods=['POST'])
@jwt_required()
def rerun_task(task_id):
    """Rerun a failed or completed task"""
    user_id = get_current_user_id()
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    # Reset task status
    task.status = 'pending'
    task.result = None
    task.completed_at = None
    db.session.commit()
    
    # Rerun task
    task_data = json.loads(task.task_data) if task.task_data else {}
    task_data.update({
        'agent_type': task.agent_type,
        'task_type': task.task_type
    })
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(agent_manager.route_task(task_data))
        
        task.status = 'completed' if result['success'] else 'failed'
        task.result = json.dumps(result)
        task.completed_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Task rerun completed',
            'result': result
        })
        
    except Exception as e:
        task.status = 'failed'
        task.result = json.dumps({'error': str(e)})
        db.session.commit()
        
        return jsonify({'error': 'Task rerun failed', 'details': str(e)}), 500

# Enhanced Financial Analysis Endpoints
@app.route('/api/insights/generate', methods=['POST'])
@jwt_required()
def generate_insights():
    """Manually trigger insight generation"""
    user_id = get_current_user_id()
    
    try:
        # Delete old insights
        FinancialInsight.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        
        # Generate new insights
        generate_insights_for_user(user_id)
        
        return jsonify({'message': 'Insights generated successfully'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to generate insights', 'details': str(e)}), 500

@app.route('/api/analysis/comprehensive', methods=['GET'])
@jwt_required()
def comprehensive_financial_analysis():
    """Comprehensive financial analysis combining all metrics"""
    user_id = get_current_user_id()
    
    try:
        # Get user's financial data
        transactions = Transaction.query.filter_by(user_id=user_id).all()
        user = User.query.get(user_id)
        profile = user.profile if user else None
        
        if not transactions:
            return jsonify({
                'message': 'No financial data available',
                'recommendations': ['Start adding transactions to see comprehensive analysis']
            })
        
        # Generate insights if needed
        generate_insights_for_user(user_id)
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame([{
            'amount': t.amount,
            'category': t.category,
            'type': t.transaction_type,
            'date': t.date
        } for t in transactions])
        
        # Comprehensive analysis
        analysis = {
            'spending_patterns': analyze_spending_patterns(df),
            'income_analysis': analyze_income_patterns(df),
            'financial_health': calculate_financial_health(df, profile),
            'recommendations': generate_financial_recommendations(df, profile),
            'predictions': predict_financial_trends(df),
            'risk_assessment': assess_financial_risks(df, profile)
        }
        
        return jsonify(analysis)
        
    except Exception as e:
        return jsonify({'error': 'Analysis failed', 'details': str(e)}), 500

@app.route('/api/analysis/goals', methods=['GET', 'POST'])
@jwt_required()
def financial_goals():
    """Manage and track financial goals"""
    user_id = get_current_user_id()
    
    if request.method == 'GET':
        # Get user's financial goals and progress
        try:
            transactions = Transaction.query.filter_by(user_id=user_id).all()
            goals_analysis = analyze_goal_progress(transactions)
            return jsonify(goals_analysis)
        except Exception as e:
            return jsonify({'error': 'Failed to load goals', 'details': str(e)}), 500
    
    elif request.method == 'POST':
        # Create new financial goal
        data = request.get_json()
        try:
            goal = create_financial_goal(user_id, data)
            return jsonify({'message': 'Goal created successfully', 'goal': goal}), 201
        except Exception as e:
            return jsonify({'error': 'Failed to create goal', 'details': str(e)}), 500

# Agent Workflow Management
@app.route('/api/workflows', methods=['GET', 'POST'])
@jwt_required()
def manage_workflows():
    """Manage multi-agent workflows"""
    user_id = get_current_user_id()
    
    if request.method == 'GET':
        workflows = AgentWorkflow.query.filter_by(user_id=user_id).all()
        return jsonify([{
            'id': w.id,
            'workflow_name': w.workflow_name,
            'agent_sequence': json.loads(w.agent_sequence),
            'current_step': w.current_step,
            'status': w.status,
            'task_ids': json.loads(w.task_ids) if w.task_ids else [],
            'created_at': w.created_at.isoformat()
        } for w in workflows])
    
    elif request.method == 'POST':
        data = request.get_json()
        try:
            workflow = create_agent_workflow(user_id, data)
            return jsonify({'message': 'Workflow created successfully', 'workflow_id': workflow.id}), 201
        except Exception as e:
            return jsonify({'error': 'Failed to create workflow', 'details': str(e)}), 500

@app.route('/api/workflows/<int:workflow_id>/execute', methods=['POST'])
@jwt_required()
def execute_workflow(workflow_id):
    """Execute a multi-agent workflow"""
    user_id = get_current_user_id()
    
    try:
        workflow = AgentWorkflow.query.filter_by(id=workflow_id, user_id=user_id).first()
        if not workflow:
            return jsonify({'error': 'Workflow not found'}), 404
        
        result = execute_agent_workflow(workflow)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': 'Workflow execution failed', 'details': str(e)}), 500

# Enhanced Agent Management
@app.route('/api/agents/<agent_type>/specialize', methods=['POST'])
@jwt_required()
def specialize_agent(agent_type):
    """Specialize an agent for specific user needs"""
    user_id = get_current_user_id()
    data = request.get_json()
    
    try:
        agent = agent_manager.get_agent(agent_type)
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        
        # Customize agent for user
        specialization = customize_agent_for_user(agent, user_id, data)
        return jsonify({'message': 'Agent specialized successfully', 'specialization': specialization})
        
    except Exception as e:
        return jsonify({'error': 'Agent specialization failed', 'details': str(e)}), 500

@app.route('/api/agents/collaborate', methods=['POST'])
@jwt_required()
def agent_collaboration():
    """Enable agents to collaborate on complex tasks"""
    user_id = get_current_user_id()
    data = request.get_json()
    
    try:
        collaboration_result = facilitate_agent_collaboration(data, user_id)
        return jsonify(collaboration_result)
        
    except Exception as e:
        return jsonify({'error': 'Agent collaboration failed', 'details': str(e)}), 500

# Helper functions for enhanced analysis
def analyze_spending_patterns(df):
    """Analyze spending patterns with ML"""
    expense_df = df[df['type'] == 'expense']
    
    if expense_df.empty:
        return {'message': 'No expense data available'}
    
    # Category analysis
    category_spending = expense_df.groupby('category')['amount'].agg(['sum', 'count', 'mean']).to_dict()
    
    # Trend analysis
    expense_df['date'] = pd.to_datetime(expense_df['date'])
    monthly_trends = expense_df.groupby(expense_df['date'].dt.to_period('M'))['amount'].sum().to_dict()
    
    # Anomaly detection using statistical methods
    anomalies = detect_spending_anomalies(expense_df)
    
    return {
        'category_analysis': category_spending,
        'monthly_trends': {str(k): float(v) for k, v in monthly_trends.items()},
        'anomalies': anomalies,
        'insights': generate_spending_insights(expense_df)
    }

def analyze_income_patterns(df):
    """Analyze income patterns for gig workers"""
    income_df = df[df['type'] == 'income']
    
    if income_df.empty:
        return {'message': 'No income data available'}
    
    income_df['date'] = pd.to_datetime(income_df['date'])
    
    # Income stability analysis
    monthly_income = income_df.groupby(income_df['date'].dt.to_period('M'))['amount'].sum()
    income_stability = calculate_income_stability(monthly_income)
    
    # Income sources
    income_sources = income_df.groupby('category')['amount'].sum().to_dict()
    
    # Seasonality patterns
    seasonality = detect_income_seasonality(income_df)
    
    return {
        'income_stability': income_stability,
        'income_sources': {k: float(v) for k, v in income_sources.items()},
        'seasonality': seasonality,
        'projections': project_income_trends(monthly_income)
    }

def calculate_financial_health(df, profile):
    """Calculate overall financial health score"""
    income_df = df[df['type'] == 'income']
    expense_df = df[df['type'] == 'expense']
    
    total_income = income_df['amount'].sum() if not income_df.empty else 0
    total_expenses = expense_df['amount'].sum() if not expense_df.empty else 0
    
    # Health metrics
    savings_rate = (total_income - total_expenses) / total_income if total_income > 0 else 0
    expense_ratio = total_expenses / total_income if total_income > 0 else 0
    
    # Risk factors
    income_volatility = calculate_income_volatility(income_df) if not income_df.empty else 0
    
    health_score = calculate_health_score(savings_rate, expense_ratio, income_volatility, profile)
    
    return {
        'health_score': health_score,
        'savings_rate': float(savings_rate),
        'expense_ratio': float(expense_ratio),
        'income_volatility': float(income_volatility),
        'risk_factors': identify_risk_factors(savings_rate, expense_ratio, income_volatility)
    }

def generate_financial_recommendations(df, profile):
    """Generate personalized financial recommendations using AI"""
    try:
        # Prepare context for Gemini
        context = prepare_recommendation_context(df, profile)
        
        prompt = f"""
        Based on the following financial data, provide 5 specific, actionable recommendations:
        
        {context}
        
        Consider:
        1. Income stability and patterns
        2. Spending habits and categories
        3. Savings opportunities
        4. Risk management
        5. Long-term financial goals
        
        Format as a JSON array of recommendations with:
        - category: (savings, investment, debt_management, budgeting, emergency_fund)
        - priority: (high, medium, low)
        - action: specific action item
        - impact: expected impact
        - timeline: recommended timeline
        """
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a financial analyst providing recommendations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        # Parse AI response
        ai_text = response.choices[0].message.content
        recommendations = parse_ai_recommendations(ai_text)
        
        return recommendations
        
    except Exception as e:
        # Fallback to rule-based recommendations
        return generate_fallback_recommendations(df, profile)

def predict_financial_trends(df):
    """Predict future financial trends using ML"""
    try:
        # Time series analysis for income and expenses
        predictions = {}
        
        # Income prediction
        income_df = df[df['type'] == 'income']
        if not income_df.empty:
            income_df['date'] = pd.to_datetime(income_df['date'])
            monthly_income = income_df.groupby(income_df['date'].dt.to_period('M'))['amount'].sum()
            predictions['income'] = predict_time_series(monthly_income)
        
        # Expense prediction
        expense_df = df[df['type'] == 'expense']
        if not expense_df.empty:
            expense_df['date'] = pd.to_datetime(expense_df['date'])
            monthly_expenses = expense_df.groupby(expense_df['date'].dt.to_period('M'))['amount'].sum()
            predictions['expenses'] = predict_time_series(monthly_expenses)
        
        return predictions
        
    except Exception as e:
        return {'error': 'Prediction failed', 'details': str(e)}

def assess_financial_risks(df, profile):
    """Assess financial risks and provide mitigation strategies"""
    risks = []
    
    # Income volatility risk
    income_df = df[df['type'] == 'income']
    if not income_df.empty:
        volatility = calculate_income_volatility(income_df)
        if volatility > 0.3:
            risks.append({
                'type': 'income_volatility',
                'severity': 'high' if volatility > 0.5 else 'medium',
                'description': 'High income volatility detected',
                'mitigation': 'Build larger emergency fund (6-12 months expenses)'
            })
    
    # Overspending risk
    expense_df = df[df['type'] == 'expense']
    income_df = df[df['type'] == 'income']
    
    if not expense_df.empty and not income_df.empty:
        total_income = income_df['amount'].sum()
        total_expenses = expense_df['amount'].sum()
        
        if total_expenses > total_income * 0.9:
            risks.append({
                'type': 'overspending',
                'severity': 'high',
                'description': 'Spending exceeds 90% of income',
                'mitigation': 'Review and reduce non-essential expenses'
            })
    
    # Emergency fund risk
    if profile and profile.employment_type in ['gig', 'informal']:
        risks.append({
            'type': 'emergency_fund',
            'severity': 'high',
            'description': 'Irregular income requires larger emergency fund',
            'mitigation': 'Build 6-12 months of expenses as emergency fund'
        })
    
    return {
        'risks': risks,
        'overall_risk_level': calculate_overall_risk(risks),
        'recommendations': generate_risk_mitigation_plan(risks)
    }

# Workflow management functions
def create_agent_workflow(user_id, data):
    """Create a new multi-agent workflow"""
    workflow = AgentWorkflow(
        user_id=user_id,
        workflow_name=data['workflow_name'],
        agent_sequence=json.dumps(data['agent_sequence']),
        task_ids=json.dumps([])
    )
    
    db.session.add(workflow)
    db.session.commit()
    
    return workflow

def prepare_workflow_task_data(workflow, task_ids, agent_type):
    """Prepare task data for workflow execution"""
    # Get previous task results if any
    previous_results = []
    if task_ids:
        for task_id in task_ids:
            task = Task.query.get(task_id)
            if task and task.result:
                previous_results.append(json.loads(task.result))
    
    return {
        'agent_type': agent_type,
        'workflow_id': workflow.id,
        'previous_results': previous_results,
        'user_id': workflow.user_id
    }

def create_workflow_task(user_id, agent_type, task_data, result):
    """Create a task record for workflow step"""
    task = Task(
        user_id=user_id,
        title=f"{agent_type} workflow task",
        description=f"Automated task from workflow",
        agent_type=agent_type,
        task_type='workflow',
        status='completed' if result.get('success') else 'failed',
        task_data=json.dumps(task_data),
        result=json.dumps(result),
        completed_at=datetime.utcnow()
    )
    db.session.add(task)
    db.session.commit()
    return task

def execute_agent_workflow(workflow):
    """Execute a multi-agent workflow step by step"""
    agent_sequence = json.loads(workflow.agent_sequence)
    task_ids = json.loads(workflow.task_ids) if workflow.task_ids else []
    
    try:
        for i, agent_type in enumerate(agent_sequence[workflow.current_step:], workflow.current_step):
            # Get agent
            agent = agent_manager.get_agent(agent_type)
            if not agent:
                raise Exception(f"Agent {agent_type} not found")
            
            # Prepare task data based on previous results
            task_data = prepare_workflow_task_data(workflow, task_ids, agent_type)
            
            # Execute task
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(agent.process_task(task_data))
            
            # Store task result
            task = create_workflow_task(workflow.user_id, agent_type, task_data, result)
            task_ids.append(task.id)
            
            # Update workflow progress
            workflow.current_step = i + 1
            workflow.task_ids = json.dumps(task_ids)
            db.session.commit()
        
        # Mark workflow as completed
        workflow.status = 'completed'
        db.session.commit()
        
        return {
            'success': True,
            'workflow_id': workflow.id,
            'task_ids': task_ids,
            'message': 'Workflow completed successfully'
        }
        
    except Exception as e:
        workflow.status = 'failed'
        db.session.commit()
        raise e

def customize_agent_for_user(agent, user_id, data):
    """Customize agent for specific user needs"""
    # Store user-specific agent preferences
    return {
        'agent_type': agent.agent_id,
        'customizations': data,
        'user_id': user_id,
        'status': 'customized'
    }

def facilitate_agent_collaboration(data, user_id):
    """Enable agents to collaborate on complex tasks"""
    collaboration_type = data.get('type', 'sequential')
    agents = data.get('agents', [])
    task_data = data.get('task_data', {})
    
    if collaboration_type == 'sequential':
        from utils import execute_sequential_collaboration
        return execute_sequential_collaboration(agents, task_data, user_id)
    elif collaboration_type == 'parallel':
        from utils import execute_parallel_collaboration
        return execute_parallel_collaboration(agents, task_data, user_id)
    else:
        raise Exception(f"Unsupported collaboration type: {collaboration_type}")

@app.route('/api/upload-financial-data', methods=['POST'])
@jwt_required()
def upload_financial_data():
    """Upload CSV/Excel file with financial data and AI will analyze and import it"""
    user_id = get_current_user_id()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext not in app.config['UPLOAD_EXTENSIONS']:
        return jsonify({'error': 'Invalid file type. Please upload CSV or Excel file'}), 400
    
    try:
        # Read file into pandas DataFrame
        if file_ext == '.csv':
            df = pd.read_csv(io.BytesIO(file.read()))
        else:  # Excel
            df = pd.read_excel(io.BytesIO(file.read()))
        
        # Use AI to analyze and categorize the data
        prompt = f"""
        Analyze this financial data and identify the columns for:
        - Date (transaction date)
        - Amount (transaction amount)
        - Description (transaction description)
        - Type (income or expense)
        - Category (spending/income category)
        
        Available columns: {list(df.columns)}
        First few rows: {df.head(3).to_dict()}
        
        Return a JSON object with the mapping:
        {{
            "date_column": "column_name",
            "amount_column": "column_name",
            "description_column": "column_name",
            "type_column": "column_name_or_null",
            "category_column": "column_name_or_null"
        }}
        
        If type or category columns don't exist, return null and I'll infer them from the data.
        """
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a financial data analyst. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        # Parse AI response
        import json as json_lib
        mapping = json_lib.loads(response.choices[0].message.content)
        
        # Process transactions for preview
        preview_transactions = []
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Extract data based on AI mapping
                date_str = str(row[mapping['date_column']])
                amount = float(row[mapping['amount_column']])
                description = str(row.get(mapping['description_column'], '')) if mapping.get('description_column') else ''
                
                # Determine transaction type
                if mapping.get('type_column') and mapping['type_column'] in df.columns:
                    trans_type = str(row[mapping['type_column']]).lower()
                    if 'income' in trans_type or 'credit' in trans_type:
                        transaction_type = 'income'
                    else:
                        transaction_type = 'expense'
                else:
                    # Infer from amount and description
                    desc_lower = description.lower()
                    
                    # FIRST: Check amount sign (most reliable for bank statements)
                    if amount > 0:
                        transaction_type = 'income'
                    elif amount < 0:
                        transaction_type = 'expense'
                    else:
                        # If amount is exactly 0, use keywords
                        income_keywords = ['salary', 'payroll', 'deposit', 'wage', 'freelance', 'consulting', 
                                         'dividend', 'interest', 'bonus', 'refund', 'reimbursement',
                                         'tax refund', 'payment from', 'cashback', 'reward', 'rebate']
                        
                        if any(keyword in desc_lower for keyword in income_keywords):
                            transaction_type = 'income'
                        else:
                            transaction_type = 'expense'
                
                amount = abs(amount)
                
                # Determine category
                if mapping.get('category_column') and mapping['category_column'] in df.columns:
                    category = str(row[mapping['category_column']])
                else:
                    # Use smart categorization
                    category = categorize_transaction(description, amount, transaction_type)
                
                # Parse date
                try:
                    trans_date = pd.to_datetime(date_str)
                except:
                    trans_date = datetime.utcnow()
                
                # Create transaction
                transaction = Transaction(
                    user_id=user_id,
                    amount=amount,
                    category=category,
                    description=description,
                    transaction_type=transaction_type,
                    date=trans_date
                )
                # Don't save yet - just collect for preview
                preview_transactions.append({
                    'date': trans_date.strftime('%Y-%m-%d'),
                    'description': description,
                    'amount': amount,
                    'type': transaction_type,
                    'category': category
                })
                
            except Exception as e:
                errors.append(f"Row {idx + 1}: {str(e)}")
                continue
        
        # Return preview data instead of saving
        return jsonify({
            'success': True,
            'preview': True,
            'message': f'Analyzed {len(preview_transactions)} transactions. Review and confirm to import.',
            'transactions': preview_transactions,
            'summary': {
                'total_transactions': len(preview_transactions),
                'total_income': sum(t['amount'] for t in preview_transactions if t['type'] == 'income'),
                'total_expenses': sum(t['amount'] for t in preview_transactions if t['type'] == 'expense'),
                'income_count': len([t for t in preview_transactions if t['type'] == 'income']),
                'expense_count': len([t for t in preview_transactions if t['type'] == 'expense'])
            },
            'errors': errors[:10]
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to process file: {str(e)}'}), 500

@app.route('/api/confirm-import', methods=['POST'])
@jwt_required()
def confirm_import():
    """Save reviewed transactions to database"""
    user_id = get_current_user_id()
    data = request.get_json()
    
    transactions = data.get('transactions', [])
    
    if not transactions:
        return jsonify({'error': 'No transactions to import'}), 400
    
    try:
        transactions_added = 0
        
        for trans_data in transactions:
            # Parse date
            try:
                trans_date = datetime.strptime(trans_data['date'], '%Y-%m-%d')
            except:
                trans_date = datetime.utcnow()
            
            # Create transaction
            transaction = Transaction(
                user_id=user_id,
                amount=float(trans_data['amount']),
                category=trans_data['category'],
                description=trans_data['description'],
                transaction_type=trans_data['type'],
                date=trans_date
            )
            db.session.add(transaction)
            transactions_added += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {transactions_added} transactions',
            'transactions_added': transactions_added
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to save transactions: {str(e)}'}), 500

# ============================================================================
# PLAID BANKING INTEGRATION
# ============================================================================

@app.route('/api/plaid/create-link-token', methods=['POST'])
@jwt_required()
def create_plaid_link_token():
    """Create Plaid Link token for user to connect bank account"""
    user_id = get_current_user_id()
    
    try:
        request_data = LinkTokenCreateRequest(
            products=[Products("transactions")],
            client_name="MultiAgent Financial",
            country_codes=[CountryCode('US')],
            language='en',
            user=LinkTokenCreateRequestUser(
                client_user_id=str(user_id)
            )
        )
        
        response = plaid_client.link_token_create(request_data)
        
        return jsonify({
            'link_token': response['link_token'],
            'expiration': response['expiration']
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to create link token: {str(e)}'}), 500

@app.route('/api/plaid/exchange-token', methods=['POST'])
@jwt_required()
def exchange_plaid_token():
    """Exchange public token for access token after user connects bank"""
    user_id = get_current_user_id()
    data = request.get_json()
    public_token = data.get('public_token')
    institution_name = data.get('institution_name', 'Unknown Bank')
    institution_id = data.get('institution_id')
    
    if not public_token:
        return jsonify({'error': 'Public token required'}), 400
    
    try:
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=public_token
        )
        
        exchange_response = plaid_client.item_public_token_exchange(exchange_request)
        access_token = exchange_response['access_token']
        item_id = exchange_response['item_id']
        
        # Store in database
        plaid_account = PlaidAccount(
            user_id=user_id,
            access_token=access_token,  # TODO: Encrypt this in production!
            item_id=item_id,
            institution_name=institution_name,
            institution_id=institution_id
        )
        db.session.add(plaid_account)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'item_id': item_id,
            'institution_name': institution_name
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to exchange token: {str(e)}'}), 500

@app.route('/api/plaid/accounts', methods=['GET'])
@jwt_required()
def get_plaid_accounts():
    """Get user's connected bank accounts"""
    user_id = get_current_user_id()
    
    accounts = PlaidAccount.query.filter_by(user_id=user_id, is_active=True).all()
    
    return jsonify([{
        'id': acc.id,
        'institution_name': acc.institution_name,
        'account_name': acc.account_name,
        'account_type': acc.account_type,
        'last_synced': acc.last_synced.isoformat() if acc.last_synced else None,
        'created_at': acc.created_at.isoformat()
    } for acc in accounts])

@app.route('/api/plaid/sync-transactions', methods=['POST'])
@jwt_required()
def sync_plaid_transactions():
    """Sync transactions from Plaid"""
    user_id = get_current_user_id()
    data = request.get_json()
    account_id = data.get('account_id')
    
    if account_id:
        plaid_accounts = [PlaidAccount.query.get(account_id)]
    else:
        plaid_accounts = PlaidAccount.query.filter_by(user_id=user_id, is_active=True).all()
    
    if not plaid_accounts:
        return jsonify({'error': 'No connected bank accounts found'}), 404
    
    total_imported = 0
    total_transactions = 0
    
    for plaid_account in plaid_accounts:
        try:
            # Use Transactions Sync API
            cursor = None
            has_more = True
            added = []
            
            while has_more:
                sync_request = TransactionsSyncRequest(
                    access_token=plaid_account.access_token,
                    cursor=cursor
                )
                
                response = plaid_client.transactions_sync(sync_request)
                
                added.extend(response['added'])
                cursor = response['next_cursor']
                has_more = response['has_more']
            
            # Import transactions
            for plaid_trans in added:
                total_transactions += 1
                
                # Check if already imported
                existing = Transaction.query.filter_by(
                    user_id=user_id,
                    description=plaid_trans['name'],
                    amount=abs(plaid_trans['amount']),
                    date=plaid_trans['date']
                ).first()
                
                if not existing:
                    # Determine type (Plaid: positive = expense, negative = income)
                    transaction_type = 'expense' if plaid_trans['amount'] > 0 else 'income'
                    amount = abs(plaid_trans['amount'])
                    
                    # Get category
                    category = plaid_trans['category'][0] if plaid_trans.get('category') else 'Other'
                    
                    transaction = Transaction(
                        user_id=user_id,
                        amount=amount,
                        category=category,
                        description=plaid_trans['name'],
                        transaction_type=transaction_type,
                        date=plaid_trans['date']
                    )
                    db.session.add(transaction)
                    total_imported += 1
            
            # Update last synced
            plaid_account.last_synced = datetime.utcnow()
            
        except Exception as e:
            print(f"Error syncing account {plaid_account.id}: {str(e)}")
            continue
    
    db.session.commit()
    
    # Generate insights after import
    try:
        generate_insights_for_user(user_id)
    except:
        pass
    
    return jsonify({
        'success': True,
        'imported': total_imported,
        'total': total_transactions,
        'message': f'Synced {total_imported} new transactions from {len(plaid_accounts)} account(s)'
    })

@app.route('/api/plaid/disconnect/<int:account_id>', methods=['DELETE'])
@jwt_required()
def disconnect_plaid_account(account_id):
    """Disconnect a Plaid account"""
    user_id = get_current_user_id()
    
    plaid_account = PlaidAccount.query.filter_by(id=account_id, user_id=user_id).first()
    
    if not plaid_account:
        return jsonify({'error': 'Account not found'}), 404
    
    plaid_account.is_active = False
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Account disconnected'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=8080)
