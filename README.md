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
  ↓
Record
  ↓
Measure
  ↓
Review
  ↓
Identify patterns
  ↓
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
      ↓
Why did it happen?
      ↓
What did I learn?
      ↓
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
## 🛠 Technology Stack

*   **Backend:** Python, Flask, Gunicorn
*   **Database:** SQLite (Relational + FTS5)
*   **Data Science:** Pandas (Import/Export/Transformation)
*   **Security:** Flask-WTF (CSRF), Flask-Bcrypt, Flask-Limiter
*   **DevOps:** Docker, ConfigParser (Environment management)

---

## 🚀 Deployment & Environment Setup

### Prerequisites
* Docker & Docker Compose (Recommended)
* OR Python 3.11+ / pip

### Quick Start (Manual)
1. **Initialize Environment:**
   ```bash
   git clone https://github.com/yourusername/sts-engine.git
   python -m venv venv
   source venv/bin/activate # Windows: venv\Scripts\activate
   pip install -r requirements.txt


<img width="1918" height="916" alt="image" src="https://github.com/user-attachments/assets/d5f25466-f339-44b7-b833-8a21950e4df6" />
<img width="1919" height="915" alt="image" src="https://github.com/user-attachments/assets/47bfbb0f-fe26-4140-b3dd-9ba7e1468b89" />
<img width="1917" height="917" alt="image" src="https://github.com/user-attachments/assets/fe0e1b4b-84b3-4c8c-a085-1259fbfde543" />
<img width="1918" height="914" alt="image" src="https://github.com/user-attachments/assets/4337c865-ff94-4b0a-a186-5eccdcee0011" />
<img width="1918" height="917" alt="image" src="https://github.com/user-attachments/assets/a949f27e-5bc8-4921-a1a8-70574772a47c" />
<img width="1918" height="916" alt="image" src="https://github.com/user-attachments/assets/62a2e930-7ec3-4099-b5e3-246f0294fba2" />
<img width="1918" height="913" alt="image" src="https://github.com/user-attachments/assets/927c79d5-b8fe-4f98-b5e1-982559860e7a" />
<img width="1918" height="915" alt="image" src="https://github.com/user-attachments/assets/97a26922-20be-4fb9-b64a-b7b7d0ed51c4" />
<img width="1917" height="914" alt="image" src="https://github.com/user-attachments/assets/178b92b3-85fc-46b8-96e0-cd175fd3f5c6" />
<img width="1917" height="909" alt="image" src="https://github.com/user-attachments/assets/accc817c-791a-41e6-9366-fa16e3128b6e" />
<img width="1918" height="915" alt="image" src="https://github.com/user-attachments/assets/8928f4df-b1b1-4e7f-a7db-93200cf4f83f" />
<img width="1916" height="914" alt="image" src="https://github.com/user-attachments/assets/9a048b91-16eb-4ffa-a96c-5af73a33df29" />


# Technology Stack
|-|-|-|-|
|Area|	Technology|
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










