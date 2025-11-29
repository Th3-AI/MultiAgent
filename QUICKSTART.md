# 🚀 Quick Start Guide

Get MultiAgent up and running in 5 minutes!

## Step 1: Get Your Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy your API key

## Step 2: Configure Environment

1. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```

2. Edit `.env` and add your API key:
   ```env
   SECRET_KEY=your-secret-key-change-this-in-production
   DATABASE_URL=sqlite:///financial_coach.db
   GEMINI_API_KEY=your-gemini-api-key-here
   ```

## Step 3: Run the Application

### Option A: Using the Startup Script (Recommended)
Simply double-click `start.bat` - it will:
- Create virtual environment
- Install dependencies
- Initialize database
- Start the server

### Option B: Manual Setup
```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Run the app
python app.py
```

## Step 4: Access the Platform

Open your browser and go to: **http://localhost:5000**

## Step 5: Create Your Account

1. Click "Sign up"
2. Enter your details
3. Start using MultiAgent!

## 🎯 First Steps

### Add Your First Transaction
1. Go to **Financial** section
2. Fill in the transaction form
3. Click "Add Transaction"

### Get AI Advice
1. In the **Financial** section
2. Type your question in the AI Advisor box
3. Click "Get AI Advice"

### Create a Task
1. Go to **Tasks** section
2. Fill in task details
3. Select an agent
4. Click "Create Task"

### View Dashboard
1. Go to **Dashboard**
2. See your financial overview
3. View charts and insights

## 💡 Tips

- **Add multiple transactions** to see better insights
- **Ask specific questions** to the AI advisor
- **Check the Dashboard** regularly for updates
- **Try different agents** for various tasks

## 🐛 Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt
```

### "Database not found" error
```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### "Port already in use" error
Edit `app.py` and change the port:
```python
app.run(debug=True, port=5001)  # Change 5000 to 5001
```

### Gemini API errors
- Check your API key in `.env`
- Verify you have API quota remaining
- Check your internet connection

## 📚 Learn More

- Read the full [README.md](README.md)
- Check the API documentation
- Explore agent capabilities

## 🎉 You're Ready!

Start managing your finances with AI-powered insights!

---

**Need help?** Create an issue on GitHub or check the documentation.
