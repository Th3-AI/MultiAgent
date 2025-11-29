"""
Sample Data Generator for MultiAgent Platform
Run this script to populate your database with sample transactions and tasks
"""

from app import app, db, User, UserProfile, Transaction, Task
from datetime import datetime, timedelta
import random

def create_sample_user():
    """Create a sample user for testing"""
    with app.app_context():
        # Check if sample user exists
        user = User.query.filter_by(email='demo@multiagent.com').first()
        
        if user:
            print("Sample user already exists!")
            return user
        
        # Create new sample user
        user = User(
            email='demo@multiagent.com',
            password='demo123',  # In production, hash this!
            name='Demo User'
        )
        db.session.add(user)
        db.session.commit()
        
        # Create user profile
        profile = UserProfile(
            user_id=user.id,
            employment_type='gig',
            monthly_income_range='3000-5000',
            financial_goals='Save for emergency fund, reduce debt, invest for retirement',
            risk_tolerance='moderate'
        )
        db.session.add(profile)
        db.session.commit()
        
        print(f"✓ Created sample user: {user.email}")
        print(f"  Password: demo123")
        return user

def create_sample_transactions(user_id):
    """Create sample transactions for the past 3 months"""
    with app.app_context():
        # Check if transactions already exist
        existing = Transaction.query.filter_by(user_id=user_id).count()
        if existing > 0:
            print(f"User already has {existing} transactions!")
            return
        
        categories = {
            'income': ['Salary', 'Freelance', 'Side Gig', 'Bonus'],
            'expense': [
                'Food & Dining', 'Transportation', 'Housing', 'Utilities',
                'Entertainment', 'Healthcare', 'Shopping', 'Insurance',
                'Debt Payment', 'Groceries'
            ]
        }
        
        transactions = []
        start_date = datetime.now() - timedelta(days=90)
        
        # Generate income transactions (2-4 per month)
        for month in range(3):
            month_start = start_date + timedelta(days=month * 30)
            income_count = random.randint(2, 4)
            
            for _ in range(income_count):
                transaction = Transaction(
                    user_id=user_id,
                    amount=random.uniform(800, 2500),
                    category=random.choice(categories['income']),
                    description=f"Income payment",
                    transaction_type='income',
                    date=month_start + timedelta(days=random.randint(0, 28))
                )
                transactions.append(transaction)
        
        # Generate expense transactions (30-50 per month)
        for month in range(3):
            month_start = start_date + timedelta(days=month * 30)
            expense_count = random.randint(30, 50)
            
            for _ in range(expense_count):
                category = random.choice(categories['expense'])
                
                # Different amount ranges for different categories
                if category == 'Housing':
                    amount = random.uniform(800, 1200)
                elif category in ['Utilities', 'Insurance']:
                    amount = random.uniform(50, 200)
                elif category == 'Groceries':
                    amount = random.uniform(30, 150)
                elif category == 'Food & Dining':
                    amount = random.uniform(10, 80)
                elif category == 'Transportation':
                    amount = random.uniform(20, 100)
                else:
                    amount = random.uniform(15, 200)
                
                transaction = Transaction(
                    user_id=user_id,
                    amount=amount,
                    category=category,
                    description=f"{category} expense",
                    transaction_type='expense',
                    date=month_start + timedelta(days=random.randint(0, 28))
                )
                transactions.append(transaction)
        
        # Add all transactions
        db.session.bulk_save_objects(transactions)
        db.session.commit()
        
        print(f"✓ Created {len(transactions)} sample transactions")
        print(f"  Income transactions: {sum(1 for t in transactions if t.transaction_type == 'income')}")
        print(f"  Expense transactions: {sum(1 for t in transactions if t.transaction_type == 'expense')}")

def create_sample_tasks(user_id):
    """Create sample tasks"""
    with app.app_context():
        # Check if tasks already exist
        existing = Task.query.filter_by(user_id=user_id).count()
        if existing > 0:
            print(f"User already has {existing} tasks!")
            return
        
        sample_tasks = [
            {
                'title': 'Analyze my spending patterns',
                'description': 'Review my expenses and identify areas where I can save money',
                'agent_type': 'financial',
                'task_type': 'spending_analysis',
                'priority': 'high'
            },
            {
                'title': 'Create a monthly budget',
                'description': 'Help me create a realistic budget based on my income and expenses',
                'agent_type': 'financial',
                'task_type': 'budget_planning',
                'priority': 'high'
            },
            {
                'title': 'Research investment options',
                'description': 'Find suitable investment opportunities for my risk tolerance',
                'agent_type': 'research',
                'task_type': 'market_research',
                'priority': 'medium'
            },
            {
                'title': 'Optimize my daily schedule',
                'description': 'Help me manage my time more effectively',
                'agent_type': 'productivity',
                'task_type': 'schedule_optimization',
                'priority': 'medium'
            },
            {
                'title': 'Learn about personal finance',
                'description': 'Create a learning path for improving my financial literacy',
                'agent_type': 'learning',
                'task_type': 'learning_path',
                'priority': 'low'
            }
        ]
        
        tasks = []
        for task_data in sample_tasks:
            task = Task(
                user_id=user_id,
                title=task_data['title'],
                description=task_data['description'],
                agent_type=task_data['agent_type'],
                task_type=task_data['task_type'],
                priority=task_data['priority'],
                status='pending'
            )
            tasks.append(task)
        
        db.session.bulk_save_objects(tasks)
        db.session.commit()
        
        print(f"✓ Created {len(tasks)} sample tasks")

def main():
    """Main function to generate all sample data"""
    print("\n" + "="*50)
    print("  MultiAgent Sample Data Generator")
    print("="*50 + "\n")
    
    try:
        # Create database tables if they don't exist
        with app.app_context():
            db.create_all()
            print("✓ Database tables ready\n")
        
        # Create sample user
        user = create_sample_user()
        print()
        
        # Create sample transactions
        create_sample_transactions(user.id)
        print()
        
        # Create sample tasks
        create_sample_tasks(user.id)
        print()
        
        print("="*50)
        print("  Sample Data Created Successfully!")
        print("="*50)
        print("\nYou can now login with:")
        print("  Email: demo@multiagent.com")
        print("  Password: demo123")
        print("\nStart the application with: python app.py")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure the database is properly configured.")

if __name__ == '__main__':
    main()
