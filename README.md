# STS — Personal Trading Journal & Quantitative Analytics

STS (Smarter Trading Systems) is a self-hosted trading journal and quantitative analytics application built for personal use.

It combines trade tracking, R-multiple analysis, journaling, screenshots, notes, and performance analytics in one private application.

The goal is simple:

Record → Measure → Review → Identify Patterns → Improve

STS is designed to help answer questions such as:

- Am I following my trading plan?
- Which setups actually have positive expectancy?
- How consistent is my execution?
- Where am I giving R back?
- Are my results improving over a meaningful sample?
- What patterns appear in my winning and losing trades?
- Is a losing trade actually a bad trade, or was it a good process with a bad outcome?

---

#Why R Instead of Money?
STS uses R-multiples as the primary performance measure.

1R represents the initial amount risked on a trade.

For example:

|Result|	Meaning|
|-|-|
|+3R|	Returned three times the initial risk|
|+1R|	Returned the initial risk|
|+0.5R|	Returned half the initial risk|
|0R|	Breakeven|
|-1R|	Lost the predefined initial risk|

This makes trades comparable regardless of account size or position size.

A €50 winner and a €500 winner are not necessarily different quality trades. If both returned +2R, they produced the same risk-adjusted result.

The purpose of STS is therefore not to make the largest monetary number appear on a dashboard.

It is to understand the distribution and consistency of trading decisions in R.

# Features
# 📊 Trading
- Create, edit, and review trades
- LONG and SHORT positions
- Entry, stop loss, and take profit tracking
- Risk/reward calculations
- Realized R tracking
- Partial position closes
- Parent/child trade relationships
- Trade notes
- Trade screenshots
- Historical trade review

# 📈 Quantitative Analytics
Current analytics include:

- Average R
- Median R
- Win rate
- Winning trades
- Losing trades
- Breakeven trades
- Profit factor
- Payoff ratio
- R distribution
- LONG vs SHORT performance
- Symbol/asset performance
- Trade duration
- Streak analysis
- Drawdown-related metrics
Performance across different time periods
The analytics layer is intentionally focused on describing the trader's historical behavior, rather than attempting to predict markets.

#🧩 Partial Position Accounting
STS treats partial closes as part of the original trade rather than as unrelated trades.

Conceptually:

```
Parent Trade
├── Partial Close #1
├── Partial Close #2
└── Partial Close #3
```

This allows the application to reconstruct the performance of a position that was managed over multiple exits.

For example:

```
Initial risk: 1R

25% closed at +2R
25% closed at +1R
50% closed at -0.5R
```

The resulting realized R is calculated using the appropriate risk weighting rather than treating each partial exit as a completely independent trade.

This is important because actual trade management often involves scaling out, partial exits, and changing exposure.

# 📝 Trading Journal

Quantitative data tells you what happened.

The journal helps explain why it happened.

STS provides space for:

Daily journal entries
- Monthly reviews
- Trade notes
- Trading rules
- Reflections
- Observations
- To-do items

The intended feedback loop is:
```
What happened?
      ↓
Why did it happen?
      ↓
What did I learn?
      ↓
What should I change?
      ↓
Did the change improve my process?
```


# 📚 Knowledge Base
STS includes a personal knowledge base for storing trading-related material.

Examples include:

- Trading notes
- Articles
- Educational material
- Concepts
- Reference material
- PDFs
- Images
- Videos
The goal is to keep research and trading review in the same environment as the actual trade history.

# 🖼️ Trading Gallery
The gallery provides a dedicated space for visual material such as:

- Chart screenshots
- Annotated setups
- Trade examples
- Market observations
- Reference images
This is particularly useful for reviewing recurring setups and building a visual library of past decisions.

#🔐 Private & Self-Hosted
STS is designed primarily for one person's private trading journal.

It is intended to run on:

- A personal computer
- A home server
- A NAS
- A private network
It is not designed to be a public SaaS application, broker, exchange, or trading execution platform.

The application should not be exposed directly to the public internet without appropriate additional security controls.

If remote access is required, a private-network solution such as a VPN is preferable to exposing the application directly to the internet.

#HTTPS
HTTPS is not currently a requirement for the intended localhost/private-network deployment.

If STS is eventually exposed through a public or untrusted network, HTTPS and additional deployment hardening should be added.

#🛡️ Security
Although STS is intended for personal use, the application includes several standard security measures:

- Password hashing
- Session-based authentication
- CSRF protection
- Login rate limiting
- Secure filename handling
- File type validation
- Request size limits
- Security headers
- Database access controls
These measures are intended to reduce common application-level risks, but they do not replace proper server, network, and backup security.

#🧮 Quantitative Philosophy
STS is built around several principles.

1. Measure the process, not just the result
A winning trade is not automatically a good trade.

A losing trade is not automatically a bad trade.

The goal is to preserve enough context to evaluate decision quality and execution, not just P&L.

2. Use risk-normalized performance
R allows trades with different position sizes to be compared on the same scale.

3. Combine quantitative and qualitative information
Numbers explain what happened.

Notes, screenshots, rules, and journal entries help explain why.

4. Prefer useful data over unnecessary complexity
STS is a personal application.
Reliable Data => Useful Analytics => Better Review => Better Decisions

# Login page
<img width="1918" height="916" alt="image" src="https://github.com/user-attachments/assets/d5f25466-f339-44b7-b833-8a21950e4df6" />

# Dashboard
<img width="1919" height="915" alt="image" src="https://github.com/user-attachments/assets/47bfbb0f-fe26-4140-b3dd-9ba7e1468b89" />

# Trade details
<img width="1917" height="917" alt="image" src="https://github.com/user-attachments/assets/fe0e1b4b-84b3-4c8c-a085-1259fbfde543" />

# Journal
<img width="1919" height="915" alt="Screenshot 2026-08-25 165523" src="https://github.com/user-attachments/assets/bc943650-4d46-4075-a812-8cda80a5a462" />

# Journal entry
<img width="1918" height="917" alt="image" src="https://github.com/user-attachments/assets/a949f27e-5bc8-4921-a1a8-70574772a47c" />

# Analytics
<img width="1918" height="916" alt="image" src="https://github.com/user-attachments/assets/62a2e930-7ec3-4099-b5e3-246f0294fba2" />


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
|Frontend| HTML/CSS/Javascript|
|Deployment|	Docker|

The stack is intentionally lightweight and suited to a self-hosted, single-user application.

# Architecture

STS uses a deliberately lightweight architecture.

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

The application intentionally avoids unnecessary infrastructure.

For a single-user trading journal, a lightweight stack is preferable to introducing distributed services that do not provide meaningful benefits for the use case.

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


#🚀 Installation
##Requirements
For local development:

- Python 3.11+
- pip
For containerized deployment:
- Docker


Clone the repository:
```
git clone https://github.com/berend21/Personal-Trading-Journal-Quantitative-Analytics.git
cd Personal-Trading-Journal-Quantitative-Analytics
```
Install dependencies:
```
pip install -r requirements.txt
```
Start application:
```
python app.py
```
Application should be available at:
```
localhost
```
##Persistent Data
Before using the Docker deployment for long-term trading history, configure persistent storage for the SQLite database and uploaded files.

Do not rely on the container filesystem as the only copy of your trading data.

#💾 Backups
Trading history is valuable data.

For long-term use, maintain regular backups of:

- SQLite database
- Uploaded images
- Knowledge-base files
- Other persistent application data
A future goal of the project is to make automated backup and restore workflows more integrated into the application.

A backup should also be periodically tested by restoring it.

#🧪 Testing
The project includes automated tests covering core trading calculations and analytics.

Run the test suite with:
```
pytest
```
The testing strategy focuses particularly on areas where incorrect calculations could affect historical performance data, including R-multiple calculations and partial-position accounting.

# Roadmap
The project is actively evolving. Areas I intend to improve include:

- Automated database backups
- Backup verification and restore workflow
- Stronger database constraints
- Cleaner database migration system

- More detailed equity curves
- Improved drawdown analysis
- MAE / MFE analysis
- More robust expectancy analysis
- Strategy/setup performance analysis
- Better sample-size awareness
- Improved performance attribution

- More detailed trade-quality tracking
- Process/adherence scoring
- Structured mistake classification
- Improved journal/analytics integration
- Better trade filtering and search

- Expanded integration test coverage
- Cleaner modular architecture
- Improved database abstraction
- CI automation

# Disclaimer

STS is a personal trading journal and analytics application.

It does not provide:

Financial advice
Investment recommendations
Trading signals
Automated trading
Broker execution
Portfolio management services
The application is intended to help record and analyze historical trading activity.

All trading decisions and associated risks remain the responsibility of the user.

#📄 License
This project is licensed under the MIT License.

See LICENSE for details.
