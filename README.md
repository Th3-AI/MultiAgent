# MultiAgent - AI-Powered Financial Platform

A sophisticated multi-agent Flask-based platform that provides intelligent financial coaching, task management, and AI-powered insights using Google Gemini API.

## 🌟 Features

### 💰 Financial Agent
- **Spending Analysis**: Track and analyze spending patterns across categories
- **Income Variability**: Monitor income stability for gig workers and freelancers
- **Budget Planning**: AI-powered personalized budget recommendations
- **Investment Guidance**: Risk-based investment strategies
- **Debt Management**: Smart debt reduction strategies
- **Emergency Fund Optimization**: Tailored savings recommendations

### 🔍 Research Agent
- Market research and competitive analysis
- Trend analysis and forecasting
- Data gathering and synthesis
- Report generation

### ⚡ Productivity Agent
- Task prioritization and scheduling
- Workflow optimization
- Time management strategies
- Habit tracking

### 📚 Learning Agent
- Skill assessment and gap analysis
- Personalized learning paths
- Resource recommendations
- Progress tracking

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Google Gemini API Key

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd Multi-Agent
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///financial_coach.db
GEMINI_API_KEY=your-gemini-api-key-here
```

5. **Run the application**
```bash
python app.py
```

6. **Access the platform**
Open your browser and navigate to: `http://localhost:5000`

## 📊 Architecture

### Backend (Flask)
- **app.py**: Main application with API endpoints
- **agents.py**: Multi-agent system implementation
- **utils.py**: Helper functions for analysis and calculations

### Frontend
- **index.html**: Modern, responsive UI
- **styles.css**: Beautiful gradient design with smooth animations
- **script.js**: Interactive dashboard with real-time updates

### Database Models
- **User**: User authentication and profile
- **UserProfile**: Financial preferences and goals
- **Transaction**: Income and expense tracking
- **FinancialInsight**: AI-generated insights
- **Task**: Agent task management
- **AgentWorkflow**: Multi-agent coordination

## 🎯 Usage

### 1. Register/Login
Create an account or login to access the platform.

### 2. Add Transactions
- Navigate to the Financial section
- Add income and expenses
- Categorize transactions for better insights

### 3. Get AI Advice
- Ask the AI Financial Advisor any question
- Get personalized recommendations
- Receive actionable insights

### 4. Create Tasks
- Assign tasks to specific agents
- Set priorities and descriptions
- Track task completion

### 5. Monitor Dashboard
- View financial health score
- Analyze spending patterns
- Track income trends
- Review AI-generated insights

## 🔧 API Endpoints

### Authentication
- `POST /api/auth/register` - Create new account
- `POST /api/auth/login` - User login

### Financial
- `GET /api/transactions` - Get all transactions
- `POST /api/transactions` - Add new transaction
- `GET /api/analysis/spending-patterns` - Spending analysis
- `GET /api/analysis/income-variability` - Income analysis
- `GET /api/analysis/comprehensive` - Full financial analysis
- `POST /api/coach/advice` - Get AI financial advice

### Tasks
- `GET /api/tasks` - Get all tasks
- `POST /api/tasks` - Create new task
- `GET /api/tasks/<id>` - Get specific task
- `PUT /api/tasks/<id>` - Update task
- `DELETE /api/tasks/<id>` - Delete task

### Agents
- `GET /api/agents` - Get agent capabilities
- `GET /api/agents/performance` - Get agent metrics
- `POST /api/agents/collaborate` - Multi-agent collaboration

### Insights
- `GET /api/insights` - Get financial insights

## 🎨 UI Features

- **Modern Gradient Design**: Beautiful purple gradient background
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Interactive Charts**: Plotly.js visualizations
- **Real-time Updates**: Live data refresh
- **Toast Notifications**: User-friendly feedback
- **Loading States**: Smooth loading animations
- **Card-based Layout**: Clean, organized interface

## 🤖 Agent System

### Agent Manager
Coordinates multiple AI agents to handle complex tasks:

1. **Task Routing**: Automatically routes tasks to appropriate agents
2. **Performance Tracking**: Monitors success rates and task counts
3. **Workflow Management**: Orchestrates multi-agent workflows
4. **Result Aggregation**: Combines insights from multiple agents

### Agent Capabilities

Each agent has specialized capabilities:
- **Financial Agent**: 8 financial analysis capabilities
- **Research Agent**: 7 research and analysis capabilities
- **Productivity Agent**: 7 productivity optimization capabilities
- **Learning Agent**: 7 learning and development capabilities

## 📈 Financial Analysis

### Metrics Calculated
- **Savings Rate**: Percentage of income saved
- **Expense Ratio**: Spending vs income
- **Income Volatility**: Income stability score
- **Financial Health Score**: Overall financial wellness (0-100)
- **Risk Assessment**: Identification of financial risks

### AI-Powered Insights
- Spending anomaly detection
- Income pattern analysis
- Budget recommendations
- Investment strategies
- Debt management plans

## 🔒 Security

- JWT-based authentication
- Password hashing (implement bcrypt in production)
- CORS protection
- SQL injection prevention via SQLAlchemy ORM
- Environment variable configuration

## 🚧 Production Deployment

### Important Security Updates

Before deploying to production:

1. **Password Hashing**
```python
from werkzeug.security import generate_password_hash, check_password_hash

# In registration
user.password = generate_password_hash(data['password'])

# In login
check_password_hash(user.password, data['password'])
```

2. **Environment Variables**
- Use strong SECRET_KEY
- Secure database connection
- Protect API keys

3. **HTTPS**
- Enable SSL/TLS
- Use secure cookies

4. **Database**
- Use PostgreSQL or MySQL
- Regular backups
- Connection pooling

## 📝 Development

### Adding New Agents

1. Create agent class in `agents.py`:
```python
class NewAgent(BaseAgent):
    def __init__(self):
        super().__init__("new_agent", "New Agent Name")
    
    def get_capabilities(self):
        return ["capability1", "capability2"]
    
    async def process_task(self, task_data):
        # Implementation
        pass
```

2. Register in AgentManager:
```python
self.agents = {
    'new': NewAgent(),
    # ... other agents
}
```

### Adding New Endpoints

Add routes in `app.py`:
```python
@app.route('/api/new-endpoint', methods=['GET', 'POST'])
@jwt_required()
def new_endpoint():
    user_id = get_jwt_identity()
    # Implementation
    return jsonify({'result': 'success'})
```

## 🐛 Troubleshooting

### Common Issues

1. **Database not found**
```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
```

2. **Gemini API errors**
- Check API key in `.env`
- Verify API quota
- Check internet connection

3. **Port already in use**
```bash
# Change port in app.py
app.run(debug=True, port=5001)
```

## 📚 Dependencies

- Flask 3.0.0 - Web framework
- Flask-SQLAlchemy 3.1.1 - Database ORM
- Flask-JWT-Extended 4.5.3 - Authentication
- Flask-CORS 4.0.0 - Cross-origin requests
- google-generativeai 0.3.1 - AI integration
- pandas 2.1.4 - Data analysis
- numpy 1.26.2 - Numerical computing
- scikit-learn 1.3.2 - Machine learning

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Google Gemini API for AI capabilities
- Flask community for excellent documentation
- Plotly.js for beautiful visualizations
- Font Awesome for icons

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check existing documentation
- Review API endpoints

## 🔮 Future Enhancements

- [ ] Mobile app (React Native)
- [ ] Real-time notifications
- [ ] Multi-currency support
- [ ] Bank account integration
- [ ] Advanced ML predictions
- [ ] Social features
- [ ] Export reports (PDF/Excel)
- [ ] Voice commands
- [ ] Dark mode
- [ ] Multi-language support

---

**Built with ❤️ using Flask, Google Gemini AI, and modern web technologies**
