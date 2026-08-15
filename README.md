# STS Engine
### *Personal Trading Journal & Quantitative Analytics*

**STS (Smarter Trading Systems)** is a personal trading journal and performance analysis application built to help me record trades, review execution, and understand my trading performance through quantitative data.

The goal is simple:

Turn trading activity into structured data that can be reviewed, measured, and learned from.

Instead of relying only on screenshots, notes, or memory, STS Engine keeps trades, partial exits, risk/reward metrics, journal entries, rules, notes, and supporting media in one disorganized place.

---

# Why STS Engine?

Trading generates a lot of information, but it is easy for that information to become fragmented.

STS Engine was built to create a structured feedback loop:

Trade
  >
Record
  >
Measure
  >
Review
  >
Identify patterns
  >
Improve

The application is primarily designed for personal use and self-hosted environments, rather than multple commercial trading platform or brokers.

# Features
# 📊 Trading & Performance
- Record and manage trades
- Track LONG and SHORT positions
- Risk/reward (R) calculations
- Track stop loss, take profit, entry and exit prices
- Support for partial position closes
- Parent/child trade relationships
- Track realized performance
- Review performance across different time periods
- Compare LONG vs SHORT performance
- Import and export trading data with Excel

# 📈 Analytics

The analytics dashboard provides a quantitative view of trading performance, including:

- Win rate
- Average R
- Median R
- Winning and losing trades
- Long/Short distribution
- Performance over different time periods
- Trade-level performance data

The purpose of these metrics is not to predict the market, but to make my own trading behavior easier to evaluate.

# 📝 Trading Journal

Keep contextual information alongside the quantitative data:

- Daily/monthly journal entries
- Trade notes
- Trading rules
- To-do items
- Reflections and observations

This creates a connection between:

What happened?
      >
Why did it happen?
      >
What did I learn?
      >
What should I do differently?

# 📚 Knowledge Base

A personal knowledge base for storing trading-related material and references.

It can be used for:

- Notes
- Articles
- Educational material
- Images
- Videos
- PDFs
- Trading concepts and references
# 🖼️ Trading Gallery

A dedicated space for storing and reviewing visual trading material such as:

- Chart screenshots
- Trade examples
- Market observations
- Annotated setups
- Reference images

# Login page
<img width="1918" height="916" alt="image" src="https://github.com/user-attachments/assets/d5f25466-f339-44b7-b833-8a21950e4df6" />

# Dashboard
<img width="1919" height="915" alt="image" src="https://github.com/user-attachments/assets/47bfbb0f-fe26-4140-b3dd-9ba7e1468b89" />

# Trade details
<img width="1917" height="917" alt="image" src="https://github.com/user-attachments/assets/fe0e1b4b-84b3-4c8c-a085-1259fbfde543" />

# Journal
<img width="1918" height="914" alt="image" src="https://github.com/user-attachments/assets/4337c865-ff94-4b0a-a186-5eccdcee0011" />

# Journal entry
<img width="1918" height="917" alt="image" src="https://github.com/user-attachments/assets/a949f27e-5bc8-4921-a1a8-70574772a47c" />

# Analytics
<img width="1918" height="916" alt="image" src="https://github.com/user-attachments/assets/62a2e930-7ec3-4099-b5e3-246f0294fba2" />

# To do list
<img width="1918" height="913" alt="image" src="https://github.com/user-attachments/assets/927c79d5-b8fe-4f98-b5e1-982559860e7a" />

# Notes
<img width="1918" height="915" alt="image" src="https://github.com/user-attachments/assets/97a26922-20be-4fb9-b64a-b7b7d0ed51c4" />

# Gallery
<img width="1917" height="914" alt="image" src="https://github.com/user-attachments/assets/178b92b3-85fc-46b8-96e0-cd175fd3f5c6" />

# Image modal
<img width="1917" height="909" alt="image" src="https://github.com/user-attachments/assets/accc817c-791a-41e6-9366-fa16e3128b6e" />

# Knowledge 
<img width="1918" height="915" alt="image" src="https://github.com/user-attachments/assets/8928f4df-b1b1-4e7f-a7db-93200cf4f83f" />

# Settings
<img width="1916" height="914" alt="image" src="https://github.com/user-attachments/assets/9a048b91-16eb-4ffa-a96c-5af73a33df29" />


# Technology Stack

|Area|Technology|
|-|-|
|Backend|	Python, Flask|
|Web Server|	Gunicorn|
|Database|	SQLite|
|Data Processing|	Pandas|
|Excel|	OpenPyXL|
|Image Processing|	Pillow|
|Authentication|	Flask-Bcrypt|
|CSRF Protection|	Flask-WTF|
|Rate Limiting|	Flask-Limiter|
|Deployment|	Docker|
|Frontend|HTML, CSS, JavaScript|

The application intentionally uses a relatively lightweight stack because it is designed primarily for personal/self-hosted use.

# Architecture

At its core, STS Engine follows a straightforward web application architecture:

                    ┌─────────────────┐
                    │     Browser     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     Flask       │
                    │   Application   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
          Trading        Analytics       Journal
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                    ┌─────────────────┐
                    │     SQLite      │
                    └─────────────────┘

Trade data is stored relationally so that a parent trade can be associated with partial closes and the resulting performance can be reconstructed.

# Data Model

A key part of the application is the relationship between an initial position and its partial closes.

Conceptually:

Parent Trade
│
├── Partial Close #1
├── Partial Close #2
└── Partial Close #3

This allows the application to preserve the relationship between the original trade and subsequent position management.

The aim is to make performance calculations reflect the actual way a position was managed rather than treating every partial exit as an unrelated trade.

# Quantitative Metrics

STS Engine uses R-based performance analysis to make trades comparable across different position sizes.

Some of the core concepts include:

Risk per trade
Realized R
Risk/reward ratio
Winning R
Losing R
Average R
Median R
Win rate
Long/Short distribution

For example, instead of looking only at monetary profit:

Trade A: +$100
Trade B: +$250
Trade C: -$75

the journal can evaluate performance in relation to the original risk:

Trade A: +1.0R
Trade B: +2.5R
Trade C: -0.75R

This makes performance easier to compare across trades.

# Import & Export

Trading data can be imported and exported using Excel files.

This makes it possible to:

Bring existing trade history into STS Engine
Edit or analyze data externally
Maintain backups of structured trade data
Move data between systems

Importing data is intended to complement the application rather than lock the trading history into a proprietary format.

# Security

Although STS Engine is primarily a personal application, it includes several standard web application security measures:

Password hashing
CSRF protection
Session-based authentication
Login rate limiting
Secure filename handling for uploads
File type validation
Database access controls

The application should still be deployed responsibly, particularly when exposed beyond a trusted local network.

STS Engine is not a broker, exchange, trading execution system, or financial service.

# Running with Docker

Docker is the preferred way to run the application.

Clone the repository:
```
git clone https://github.com/berend21/STS-Engine-Quantitative-Data-Pipeline.git
cd STS-Engine-Quantitative-Data-Pipeline
```
Build the image:
```
docker build -t sts-engine .
```
Run the application:
```
docker run -d \
  --name sts-engine \
  -p 5050:5050 \
  sts-engine
```
Then open:
```
http://localhost:5050
```
Configuration and persistent storage should be reviewed before using the container for long-term data storage.

# Running Locally
Requirements
- Python 3.11+
- pip

Install dependencies:
```
pip install -r requirements.txt
```
Run the application:
```
python app.py
```
The application will then be available locally.

# Design Philosophy

STS Engine is built around a few principles:

1. Record the process, not just the result.
A winning trade does not automatically mean a good trade, and a losing trade does not automatically mean a bad trade.
The goal is to preserve enough context to understand how and why the result occurred.

2. Measure in R
Risk-normalized metrics make trades more comparable and make performance easier to evaluate independently of position size and to remove the money part.

3. Keep quantitative and qualitative information together
Numbers explain what happened.
Journal entries, notes, rules, and screenshots help explain why.
STS Engine is designed to keep both sides of that process together.

4. Prefer useful data over unnecessary complexity
This is a personal application. The goal is not to build an enterprise trading platform.
The priority is:

Reliable data
    >
Useful analytics
    >
Better review
    >
Better decisions

# Roadmap

- Possible future improvements include:
- More detailed equity curve analysis
- Drawdown analysis
- Improved trade statistics
- Strategy/setup performance analysis
- Better data validation
- Automated database backups
- More comprehensive testing
- Improved trade filtering and search
- More detailed journal/analytics integration
- Cleaner modular application architecture

# Disclaimer

STS Engine is a personal trading journal and analytics tool.

It does not provide financial advice, investment recommendations, trading signals, or automated execution.

All trading decisions and associated risks remain the responsibility of the user.
