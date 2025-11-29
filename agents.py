from abc import ABC, abstractmethod
from typing import Dict, Any, List
import google.generativeai as genai
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Configure OpenAI API (PipeShift)
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_BASE_URL', 'https://api.pipeshift.com/api/v0/')
)
AI_MODEL = os.getenv('OPENAI_MODEL', 'neysa-qwen3-vl-30b-a3b')

def get_ai_response(prompt: str, system_message: str = "You are a helpful AI assistant.") -> str:
    """Helper function to get AI response using OpenAI"""
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error getting AI response: {str(e)}"

class BaseAgent(ABC):
    """Base class for all agent types"""
    
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.created_at = datetime.utcnow()
        self.task_count = 0
        self.success_rate = 0.0
    
    @abstractmethod
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task and return results"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities"""
        pass
    
    def update_performance(self, success: bool):
        """Update agent performance metrics"""
        self.task_count += 1
        if self.task_count == 1:
            self.success_rate = 1.0 if success else 0.0
        else:
            self.success_rate = (self.success_rate * (self.task_count - 1) + (1.0 if success else 0.0)) / self.task_count

class FinancialAgent(BaseAgent):
    """Financial coaching and analysis agent"""
    
    def __init__(self):
        super().__init__("financial_agent", "Financial Coach")
        self.specializations = [
            "spending_analysis", "income_variability", "budget_planning",
            "investment_guidance", "debt_management", "emergency_fund_optimization"
        ]
    
    def get_capabilities(self) -> List[str]:
        return [
            "Analyze spending patterns and identify trends",
            "Assess income stability and variability",
            "Create personalized budgets",
            "Provide investment recommendations",
            "Develop debt reduction strategies",
            "Optimize emergency fund planning",
            "Generate financial health reports",
            "Predict financial trends"
        ]
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process financial analysis tasks"""
        try:
            task_type = task_data.get('task_type', 'general')
            
            if task_type == 'spending_analysis':
                return await self.analyze_spending_patterns(task_data)
            elif task_type == 'income_analysis':
                return await self.analyze_income_patterns(task_data)
            elif task_type == 'budget_planning':
                return await self.create_budget_plan(task_data)
            elif task_type == 'investment_guidance':
                return await self.provide_investment_advice(task_data)
            elif task_type == 'debt_management':
                return await self.analyze_debt_strategy(task_data)
            elif task_type == 'comprehensive_analysis':
                return await self.comprehensive_financial_analysis(task_data)
            else:
                return await self.general_financial_advice(task_data)
                
        except Exception as e:
            self.update_performance(False)
            return {
                'success': False,
                'error': str(e),
                'agent_type': 'financial',
                'task_type': task_type
            }
    
    async def analyze_spending_patterns(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze spending patterns and provide insights"""
        transactions = task_data.get('transactions', [])
        
        if not transactions:
            return {
                'success': True,
                'message': 'No transaction data available',
                'recommendations': ['Start adding transactions to see spending patterns']
            }
        
        # Analyze spending by category
        expense_transactions = [t for t in transactions if t.get('type') == 'expense']
        category_spending = {}
        
        for transaction in expense_transactions:
            category = transaction.get('category', 'uncategorized')
            amount = transaction.get('amount', 0)
            category_spending[category] = category_spending.get(category, 0) + abs(amount)
        
        # Generate insights
        total_spending = sum(category_spending.values())
        insights = []
        
        # Top spending category
        if category_spending:
            top_category = max(category_spending, key=category_spending.get)
            top_percentage = (category_spending[top_category] / total_spending) * 100
            
            if top_percentage > 40:
                insights.append(f"{top_percentage:.1f}% of spending is in {top_category}")
        
        # Generate AI-powered advice
        context = f"Spending by category: {category_spending}"
        advice = await self.generate_ai_advice(context, "spending_patterns")
        
        self.update_performance(True)
        
        return {
            'success': True,
            'agent_type': 'financial',
            'task_type': 'spending_analysis',
            'category_spending': category_spending,
            'total_spending': total_spending,
            'insights': insights,
            'recommendations': advice
        }
    
    async def analyze_income_patterns(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze income patterns for stability and trends"""
        transactions = task_data.get('transactions', [])
        
        income_transactions = [t for t in transactions if t.get('type') == 'income']
        
        if not income_transactions:
            return {
                'success': True,
                'message': 'No income data available',
                'recommendations': ['Add income transactions to see income patterns']
            }
        
        # Group income by month
        monthly_income = {}
        for transaction in income_transactions:
            date_str = transaction.get('date', '')
            if date_str:
                try:
                    date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    month_key = date.strftime('%Y-%m')
                    amount = transaction.get('amount', 0)
                    monthly_income[month_key] = monthly_income.get(month_key, 0) + amount
                except:
                    continue
        
        # Calculate stability metrics
        if len(monthly_income) >= 2:
            income_values = list(monthly_income.values())
            mean_income = sum(income_values) / len(income_values)
            variance = sum((x - mean_income) ** 2 for x in income_values) / len(income_values)
            std_dev = variance ** 0.5
            volatility = (std_dev / mean_income) if mean_income > 0 else 0
        else:
            volatility = 0
        
        # Generate AI advice
        context = f"Monthly income: {monthly_income}, Volatility: {volatility:.2f}"
        advice = await self.generate_ai_advice(context, "income_stability")
        
        self.update_performance(True)
        
        return {
            'success': True,
            'agent_type': 'financial',
            'task_type': 'income_analysis',
            'monthly_income': monthly_income,
            'volatility': volatility,
            'stability_score': max(0, 1 - volatility),
            'recommendations': advice
        }
    
    async def create_budget_plan(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create personalized budget plan"""
        transactions = task_data.get('transactions', [])
        monthly_income = task_data.get('monthly_income', 0)
        
        # Calculate average monthly spending by category
        expense_transactions = [t for t in transactions if t.get('type') == 'expense']
        category_spending = {}
        
        for transaction in expense_transactions:
            category = transaction.get('category', 'uncategorized')
            amount = transaction.get('amount', 0)
            category_spending[category] = category_spending.get(category, 0) + abs(amount)
        
        # Create budget recommendations
        total_expenses = sum(category_spending.values())
        budget_recommendations = {}
        
        # Standard budgeting rules (50/30/20 rule)
        if monthly_income > 0:
            budget_recommendations = {
                'needs': monthly_income * 0.5,      # 50% for needs
                'wants': monthly_income * 0.3,      # 30% for wants
                'savings': monthly_income * 0.2     # 20% for savings
            }
        
        # Category-specific recommendations
        category_budgets = {}
        for category, amount in category_spending.items():
            # Recommend reducing overspending categories by 10-20%
            if amount > (monthly_income * 0.1):  # More than 10% of income
                category_budgets[category] = amount * 0.85  # Reduce by 15%
            else:
                category_budgets[category] = amount
        
        # Generate AI advice
        context = f"Current spending: {category_spending}, Monthly income: {monthly_income}"
        advice = await self.generate_ai_advice(context, "budget_planning")
        
        self.update_performance(True)
        
        return {
            'success': True,
            'agent_type': 'financial',
            'task_type': 'budget_planning',
            'budget_recommendations': budget_recommendations,
            'category_budgets': category_budgets,
            'total_expenses': total_expenses,
            'recommendations': advice
        }
    
    async def provide_investment_advice(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide investment guidance based on financial profile"""
        risk_tolerance = task_data.get('risk_tolerance', 'moderate')
        monthly_income = task_data.get('monthly_income', 0)
        investment_goals = task_data.get('investment_goals', [])
        
        # Risk-based investment recommendations
        investment_strategies = {
            'conservative': {
                'allocation': {'bonds': 60, 'stocks': 30, 'cash': 10},
                'recommended_funds': ['Index funds', 'Government bonds', 'High-yield savings'],
                'expected_return': '4-6% annually'
            },
            'moderate': {
                'allocation': {'bonds': 40, 'stocks': 50, 'cash': 10},
                'recommended_funds': ['Balanced index funds', 'ETFs', 'Some growth stocks'],
                'expected_return': '6-8% annually'
            },
            'aggressive': {
                'allocation': {'bonds': 20, 'stocks': 70, 'cash': 10},
                'recommended_funds': ['Growth stocks', 'Tech ETFs', 'Emerging markets'],
                'expected_return': '8-12% annually'
            }
        }
        
        strategy = investment_strategies.get(risk_tolerance, investment_strategies['moderate'])
        
        # Calculate investment amount (20% of income recommendation)
        investment_amount = monthly_income * 0.2
        
        # Generate AI advice
        context = f"Risk tolerance: {risk_tolerance}, Monthly income: {monthly_income}, Goals: {investment_goals}"
        advice = await self.generate_ai_advice(context, "investment_guidance")
        
        self.update_performance(True)
        
        return {
            'success': True,
            'agent_type': 'financial',
            'task_type': 'investment_guidance',
            'strategy': strategy,
            'recommended_monthly_investment': investment_amount,
            'recommendations': advice
        }
    
    async def analyze_debt_strategy(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze and recommend debt management strategies"""
        debts = task_data.get('debts', [])
        monthly_income = task_data.get('monthly_income', 0)
        
        if not debts:
            return {
                'success': True,
                'message': 'No debt data available',
                'recommendations': ['Continue debt-free status']
            }
        
        total_debt = sum(debt.get('amount', 0) for debt in debts)
        total_monthly_payments = sum(debt.get('monthly_payment', 0) for debt in debts)
        
        # Calculate debt-to-income ratio
        debt_to_income = (total_monthly_payments / monthly_income) if monthly_income > 0 else 0
        
        # Prioritize debts (highest interest rate first)
        prioritized_debts = sorted(debts, key=lambda x: x.get('interest_rate', 0), reverse=True)
        
        # Generate payoff strategies
        strategies = {
            'avalanche': {
                'description': 'Pay highest interest debt first',
                'total_interest_saved': 'Maximum',
                'time_to_debt_free': 'Fastest for high-interest debt'
            },
            'snowball': {
                'description': 'Pay smallest debt first',
                'total_interest_saved': 'More than minimum payments',
                'time_to_debt_free': 'Psychological wins'
            }
        }
        
        # Generate AI advice
        context = f"Total debt: {total_debt}, Debt-to-income: {debt_to_income:.2f}, Debts: {debts}"
        advice = await self.generate_ai_advice(context, "debt_management")
        
        self.update_performance(True)
        
        return {
            'success': True,
            'agent_type': 'financial',
            'task_type': 'debt_management',
            'total_debt': total_debt,
            'debt_to_income_ratio': debt_to_income,
            'prioritized_debts': prioritized_debts,
            'strategies': strategies,
            'recommendations': advice
        }
    
    async def comprehensive_financial_analysis(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive financial analysis"""
        transactions = task_data.get('transactions', [])
        profile = task_data.get('profile', {})
        
        # Run multiple analyses
        spending_result = await self.analyze_spending_patterns(task_data)
        income_result = await self.analyze_income_patterns(task_data)
        budget_result = await self.create_budget_plan(task_data)
        
        # Calculate overall financial health
        income_transactions = [t for t in transactions if t.get('type') == 'income']
        expense_transactions = [t for t in transactions if t.get('type') == 'expense']
        
        total_income = sum(t.get('amount', 0) for t in income_transactions)
        total_expenses = sum(t.get('amount', 0) for t in expense_transactions)
        
        savings_rate = (total_income - total_expenses) / total_income if total_income > 0 else 0
        
        # Calculate health score
        health_score = self.calculate_health_score(savings_rate, income_result.get('volatility', 0), profile)
        
        # Generate comprehensive AI advice
        context = f"""
        Financial Profile:
        - Total Income: ${total_income:.2f}
        - Total Expenses: ${total_expenses:.2f}
        - Savings Rate: {savings_rate:.2%}
        - Income Volatility: {income_result.get('volatility', 0):.2f}
        - Employment Type: {profile.get('employment_type', 'unknown')}
        """
        
        comprehensive_advice = await self.generate_ai_advice(context, "comprehensive_analysis")
        
        self.update_performance(True)
        
        return {
            'success': True,
            'agent_type': 'financial',
            'task_type': 'comprehensive_analysis',
            'health_score': health_score,
            'savings_rate': savings_rate,
            'spending_analysis': spending_result,
            'income_analysis': income_result,
            'budget_plan': budget_result,
            'comprehensive_recommendations': comprehensive_advice
        }
    
    async def general_financial_advice(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide general financial advice"""
        context = json.dumps(task_data, indent=2)
        advice = await self.generate_ai_advice(context, "general_advice")
        
        self.update_performance(True)
        
        return {
            'success': True,
            'agent_type': 'financial',
            'task_type': 'general_advice',
            'recommendations': advice
        }
    
    async def generate_ai_advice(self, context: str, advice_type: str) -> List[str]:
        """Generate AI-powered financial advice using Gemini"""
        try:
            prompt = f"""
            As a financial coach, provide specific, actionable advice based on this context:
            
            Context: {context}
            Advice Type: {advice_type}
            
            Provide 3-5 specific recommendations. Each recommendation should be:
            - Actionable and specific
            - Tailored to the financial situation
            - Include expected outcomes
            - Be realistic and practical
            
            Format as a JSON array of strings.
            """
            
            response_text = get_ai_response(prompt, "You are an expert financial coach.")
            
            # Parse the response
            try:
                advice_list = json.loads(response_text)
                if isinstance(advice_list, list):
                    return advice_list
            except:
                # Fallback: extract advice from text
                advice_text = response_text
                recommendations = []
                lines = advice_text.split('\n')
                for line in lines:
                    if line.strip() and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                        recommendations.append(line.strip('-•* ').strip())
                
                return recommendations[:5]  # Limit to 5 recommendations
            
            return ["Focus on increasing your savings rate", "Review and reduce unnecessary expenses", "Build an emergency fund"]
            
        except Exception as e:
            # Fallback recommendations
            return [
                "Track your spending to identify areas for improvement",
                "Aim to save at least 20% of your income",
                "Build an emergency fund covering 3-6 months of expenses"
            ]
    
    def calculate_health_score(self, savings_rate: float, income_volatility: float, profile: Dict) -> int:
        """Calculate financial health score (0-100)"""
        score = 50  # Base score
        
        # Savings rate impact
        if savings_rate >= 0.2:
            score += 30
        elif savings_rate >= 0.1:
            score += 20
        elif savings_rate >= 0.05:
            score += 10
        
        # Income volatility impact
        if income_volatility <= 0.1:
            score += 15
        elif income_volatility <= 0.2:
            score += 10
        elif income_volatility <= 0.3:
            score += 5
        
        # Employment type adjustment
        if profile.get('employment_type') in ['gig', 'informal']:
            score -= 10
        
        return max(0, min(100, score))
        return [
            "financial_analysis",
            "budget_planning",
            "investment_advice",
            "spending_pattern_analysis",
            "income_optimization",
            "debt_management",
            "savings_recommendations"
        ]
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process financial-related tasks"""
        task_type = task_data.get('task_type', 'general_advice')
        
        try:
            if task_type == 'spending_analysis':
                return await self.analyze_spending_patterns(task_data)
            elif task_type == 'budget_planning':
                return await self.create_budget_plan(task_data)
            elif task_type == 'investment_advice':
                return await self.provide_investment_advice(task_data)
            elif task_type == 'debt_management':
                return await self.analyze_debt_situation(task_data)
            else:
                return await self.general_financial_advice(task_data)
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'agent_id': self.agent_id
            }
    
    async def analyze_spending_patterns(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user spending patterns and provide insights"""
        transactions = data.get('transactions', [])
        user_profile = data.get('user_profile', {})
        
        prompt = f"""
        As a financial analyst, analyze these spending patterns:
        
        User Profile: {user_profile}
        Recent Transactions: {transactions}
        
        Provide:
        1. Spending category breakdown
        2. Unusual spending patterns
        3. Cost-saving opportunities
        4. Budget recommendations
        """
        
        response_text = get_ai_response(prompt, "You are a financial analyst.")
        
        return {
            'success': True,
            'analysis': response_text,
            'agent_id': self.agent_id,
            'task_type': 'spending_analysis'
        }
    
    async def create_budget_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create personalized budget plan"""
        income = data.get('income', {})
        expenses = data.get('expenses', {})
        goals = data.get('financial_goals', '')
        
        prompt = f"""
        Create a comprehensive budget plan based on:
        
        Monthly Income: {income}
        Current Expenses: {expenses}
        Financial Goals: {goals}
        
        Provide:
        1. Recommended budget allocations
        2. Savings targets
        3. Expense reduction strategies
        4. Emergency fund recommendations
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'budget_plan': response_text,
            'agent_id': self.agent_id,
            'task_type': 'budget_planning'
        }
    
    async def provide_investment_advice(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide investment recommendations"""
        risk_tolerance = data.get('risk_tolerance', 'medium')
        investment_amount = data.get('amount', 0)
        time_horizon = data.get('time_horizon', 'medium_term')
        
        prompt = f"""
        Provide investment advice for:
        
        Risk Tolerance: {risk_tolerance}
        Investment Amount: ${investment_amount}
        Time Horizon: {time_horizon}
        
        Consider:
        1. Diversification strategies
        2. Risk-appropriate investments
        3. Long-term growth potential
        4. Market conditions
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'investment_advice': response_text,
            'agent_id': self.agent_id,
            'task_type': 'investment_advice'
        }
    
    async def analyze_debt_situation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze debt and provide repayment strategies"""
        debts = data.get('debts', [])
        income = data.get('income', {})
        
        prompt = f"""
        Analyze this debt situation and provide repayment strategies:
        
        Debts: {debts}
        Monthly Income: {income}
        
        Provide:
        1. Debt prioritization strategy
        2. Repayment timeline
        3. Consolidation options
        4. Interest-saving strategies
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'debt_analysis': response_text,
            'agent_id': self.agent_id,
            'task_type': 'debt_management'
        }
    
    async def general_financial_advice(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide general financial advice"""
        context = data.get('context', '')
        user_profile = data.get('user_profile', {})
        
        prompt = f"""
        Provide financial advice for:
        
        User Situation: {user_profile}
        Specific Context: {context}
        
        Give practical, actionable advice considering:
        1. Current financial situation
        2. Short-term and long-term goals
        3. Risk tolerance
        4. Market conditions
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'advice': response_text,
            'agent_id': self.agent_id,
            'task_type': 'general_advice'
        }

class ResearchAgent(BaseAgent):
    """Research and information gathering agent"""
    
    def __init__(self):
        super().__init__("research_agent", "Research Assistant")
    
    def get_capabilities(self) -> List[str]:
        return [
            "web_research",
            "data_analysis",
            "market_research",
            "competitive_analysis",
            "trend_analysis",
            "report_generation",
            "fact_checking"
        ]
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process research-related tasks"""
        task_type = task_data.get('task_type', 'general_research')
        
        try:
            if task_type == 'market_research':
                return await self.conduct_market_research(task_data)
            elif task_type == 'competitive_analysis':
                return await self.analyze_competition(task_data)
            elif task_type == 'trend_analysis':
                return await self.analyze_trends(task_data)
            else:
                return await self.general_research(task_data)
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'agent_id': self.agent_id
            }
    
    async def conduct_market_research(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct market research on given topic"""
        topic = data.get('topic', '')
        focus_areas = data.get('focus_areas', [])
        
        prompt = f"""
        Conduct comprehensive market research on: {topic}
        
        Focus Areas: {focus_areas}
        
        Provide:
        1. Market size and growth potential
        2. Key players and competitors
        3. Market trends and opportunities
        4. Challenges and risks
        5. Recommendations
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'research': response_text,
            'agent_id': self.agent_id,
            'task_type': 'market_research'
        }
    
    async def analyze_competition(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze competitive landscape"""
        competitors = data.get('competitors', [])
        industry = data.get('industry', '')
        
        prompt = f"""
        Analyze competitive landscape for:
        
        Industry: {industry}
        Competitors: {competitors}
        
        Provide:
        1. Competitive positioning
        2. Strengths and weaknesses analysis
        3. Market share analysis
        4. Strategic recommendations
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'competitive_analysis': response_text,
            'agent_id': self.agent_id,
            'task_type': 'competitive_analysis'
        }
    
    async def analyze_trends(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze industry or market trends"""
        domain = data.get('domain', '')
        time_period = data.get('time_period', 'current')
        
        prompt = f"""
        Analyze trends in {domain} for {time_period} period:
        
        Provide:
        1. Current trends
        2. Emerging patterns
        3. Future predictions
        4. Impact assessment
        5. Opportunities and threats
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'trend_analysis': response_text,
            'agent_id': self.agent_id,
            'task_type': 'trend_analysis'
        }
    
    async def general_research(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct general research on any topic"""
        query = data.get('query', '')
        depth = data.get('depth', 'comprehensive')
        
        prompt = f"""
        Research the following topic: {query}
        
        Depth level: {depth}
        
        Provide comprehensive information including:
        1. Key facts and figures
        2. Historical context
        3. Current status
        4. Future outlook
        5. Sources and references
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'research': response_text,
            'agent_id': self.agent_id,
            'task_type': 'general_research'
        }

class ProductivityAgent(BaseAgent):
    """Productivity and task management agent"""
    
    def __init__(self):
        super().__init__("productivity_agent", "Productivity Coach")
    
    def get_capabilities(self) -> List[str]:
        return [
            "task_prioritization",
            "time_management",
            "workflow_optimization",
            "habit_tracking",
            "goal_setting",
            "schedule_optimization",
            "productivity_analysis"
        ]
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process productivity-related tasks"""
        task_type = task_data.get('task_type', 'general_productivity')
        
        try:
            if task_type == 'task_prioritization':
                return await self.prioritize_tasks(task_data)
            elif task_type == 'schedule_optimization':
                return await self.optimize_schedule(task_data)
            elif task_type == 'workflow_analysis':
                return await self.analyze_workflow(task_data)
            else:
                return await self.general_productivity_advice(task_data)
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'agent_id': self.agent_id
            }
    
    async def prioritize_tasks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prioritize tasks based on various criteria"""
        tasks = data.get('tasks', [])
        criteria = data.get('criteria', ['urgency', 'importance', 'effort'])
        
        prompt = f"""
        Prioritize these tasks based on {criteria}:
        
        Tasks: {tasks}
        
        Provide:
        1. Prioritized task list
        2. Rationale for prioritization
        3. Recommended order of execution
        4. Time estimates
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'prioritization': response_text,
            'agent_id': self.agent_id,
            'task_type': 'task_prioritization'
        }
    
    async def optimize_schedule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize user's schedule"""
        current_schedule = data.get('schedule', {})
        constraints = data.get('constraints', {})
        goals = data.get('goals', '')
        
        prompt = f"""
        Optimize this schedule:
        
        Current Schedule: {current_schedule}
        Constraints: {constraints}
        Goals: {goals}
        
        Provide:
        1. Optimized schedule
        2. Time blocking recommendations
        3. Break suggestions
        4. Productivity improvements
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'optimized_schedule': response_text,
            'agent_id': self.agent_id,
            'task_type': 'schedule_optimization'
        }
    
    async def analyze_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze and improve workflow"""
        workflow = data.get('workflow', {})
        pain_points = data.get('pain_points', [])
        
        prompt = f"""
        Analyze and improve this workflow:
        
        Current Workflow: {workflow}
        Pain Points: {pain_points}
        
        Provide:
        1. Workflow analysis
        2. Bottleneck identification
        3. Improvement recommendations
        4. Automation opportunities
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'workflow_analysis': response_text,
            'agent_id': self.agent_id,
            'task_type': 'workflow_analysis'
        }
    
    async def general_productivity_advice(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide general productivity advice"""
        context = data.get('context', '')
        challenges = data.get('challenges', [])
        
        prompt = f"""
        Provide productivity advice for:
        
        Context: {context}
        Challenges: {challenges}
        
        Provide:
        1. Specific strategies
        2. Tool recommendations
        3. Habit formation tips
        4. Motivation techniques
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'productivity_advice': response_text,
            'agent_id': self.agent_id,
            'task_type': 'general_productivity'
        }

class LearningAgent(BaseAgent):
    """Learning and skill development agent"""
    
    def __init__(self):
        super().__init__("learning_agent", "Learning Coach")
    
    def get_capabilities(self) -> List[str]:
        return [
            "skill_assessment",
            "learning_path_creation",
            "resource_recommendation",
            "progress_tracking",
            "knowledge_testing",
            "study_planning",
            "career_guidance"
        ]
    
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process learning-related tasks"""
        task_type = task_data.get('task_type', 'general_learning')
        
        try:
            if task_type == 'skill_assessment':
                return await self.assess_skills(task_data)
            elif task_type == 'learning_path':
                return await self.create_learning_path(task_data)
            elif task_type == 'resource_recommendation':
                return await self.recommend_resources(task_data)
            else:
                return await self.general_learning_advice(task_data)
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'agent_id': self.agent_id
            }
    
    async def assess_skills(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess current skills and identify gaps"""
        current_skills = data.get('current_skills', [])
        target_skills = data.get('target_skills', [])
        career_goals = data.get('career_goals', '')
        
        prompt = f"""
        Assess skills and identify gaps:
        
        Current Skills: {current_skills}
        Target Skills: {target_skills}
        Career Goals: {career_goals}
        
        Provide:
        1. Skill gap analysis
        2. Proficiency assessment
        3. Priority areas for development
        4. Skill acquisition timeline
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'skill_assessment': response_text,
            'agent_id': self.agent_id,
            'task_type': 'skill_assessment'
        }
    
    async def create_learning_path(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create personalized learning path"""
        subject = data.get('subject', '')
        current_level = data.get('current_level', 'beginner')
        target_level = data.get('target_level', 'intermediate')
        time_available = data.get('time_available', '2_hours_per_week')
        
        prompt = f"""
        Create a learning path for {subject}:
        
        Current Level: {current_level}
        Target Level: {target_level}
        Time Available: {time_available}
        
        Provide:
        1. Step-by-step learning roadmap
        2. Milestone definitions
        3. Time estimates for each stage
        4. Progress tracking methods
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'learning_path': response_text,
            'agent_id': self.agent_id,
            'task_type': 'learning_path'
        }
    
    async def recommend_resources(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend learning resources"""
        topic = data.get('topic', '')
        learning_style = data.get('learning_style', 'visual')
        budget = data.get('budget', 'free')
        
        prompt = f"""
        Recommend learning resources for {topic}:
        
        Learning Style: {learning_style}
        Budget: {budget}
        
        Provide:
        1. Best courses and tutorials
        2. Books and documentation
        3. Practice projects
        4. Community resources
        5. Tools and software
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'resource_recommendations': response_text,
            'agent_id': self.agent_id,
            'task_type': 'resource_recommendation'
        }
    
    async def general_learning_advice(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide general learning advice"""
        context = data.get('context', '')
        challenges = data.get('challenges', [])
        
        prompt = f"""
        Provide learning advice for:
        
        Context: {context}
        Challenges: {challenges}
        
        Provide:
        1. Learning strategies
        2. Memory techniques
        3. Study habits
        4. Motivation tips
        5. Overcoming plateaus
        """
        
        response_text = get_ai_response(prompt, "You are a helpful AI assistant.")
        
        return {
            'success': True,
            'learning_advice': response_text,
            'agent_id': self.agent_id,
            'task_type': 'general_learning'
        }

class AgentManager:
    """Manages and coordinates different agents"""
    
    def __init__(self):
        self.agents = {
            'financial': FinancialAgent(),
            'research': ResearchAgent(),
            'productivity': ProductivityAgent(),
            'learning': LearningAgent()
        }
        self.task_queue = []
        self.active_tasks = {}
    
    def get_agent(self, agent_type: str) -> BaseAgent:
        """Get agent by type"""
        return self.agents.get(agent_type)
    
    def get_all_agents(self) -> Dict[str, BaseAgent]:
        """Get all available agents"""
        return self.agents
    
    def get_agent_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities of all agents"""
        return {agent_type: agent.get_capabilities() 
                for agent_type, agent in self.agents.items()}
    
    async def route_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Route task to appropriate agent"""
        agent_type = task_data.get('agent_type', 'financial')
        
        if agent_type not in self.agents:
            return {
                'success': False,
                'error': f'Agent type {agent_type} not available'
            }
        
        agent = self.agents[agent_type]
        task_id = f"task_{len(self.active_tasks) + 1}"
        
        # Add to active tasks
        self.active_tasks[task_id] = {
            'agent_type': agent_type,
            'task_data': task_data,
            'status': 'processing',
            'created_at': datetime.utcnow()
        }
        
        try:
            result = await agent.process_task(task_data)
            
            # Update task status
            self.active_tasks[task_id]['status'] = 'completed'
            self.active_tasks[task_id]['result'] = result
            self.active_tasks[task_id]['completed_at'] = datetime.utcnow()
            
            # Update agent performance
            agent.update_performance(result.get('success', False))
            
            return {
                'success': True,
                'task_id': task_id,
                'result': result
            }
            
        except Exception as e:
            self.active_tasks[task_id]['status'] = 'failed'
            self.active_tasks[task_id]['error'] = str(e)
            agent.update_performance(False)
            
            return {
                'success': False,
                'task_id': task_id,
                'error': str(e)
            }
    
    def get_agent_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for all agents"""
        return {
            agent_type: {
                'name': agent.name,
                'task_count': agent.task_count,
                'success_rate': agent.success_rate,
                'capabilities': agent.get_capabilities()
            }
            for agent_type, agent in self.agents.items()
        }
    
    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all active and recent tasks"""
        return self.active_tasks
