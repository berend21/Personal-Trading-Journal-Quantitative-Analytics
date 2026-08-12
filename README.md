# STS Engine
### *High-Integrity Financial Data Analytics & Transactional Pipeline*

**STS (Smarter Trading Systems)** is a secure, containerized full-stack architecture designed for the rigorous logging and quantitative analysis of transactional data. This platform bridges the gap between raw trading execution and actionable performance data.

---

## 🛠 Engineering Highlights

*   **Defensive Security Architecture:** Engineered with high-level security protocols including **CSRF protection**, **Bcrypt password hashing**, and secure session management to protect sensitive financial data.
*   **Database Schema Evolution:** Implemented custom **migration logic** to handle schema changes (such as the JSON-based multi-image gallery migration) without data loss or downtime.
*   **Complex Data Relationships:** Developed a robust **Parent-Child relational model** in SQLite to accurately track and reconcile partial position closes against their parent entries.
*   **Performance-Optimized Indexing:** Leveraged custom SQL indexing and **FTS (Full-Text Search)** to maintain sub-second query performance across large datasets of trades, articles, and logs.
*   **Scalable Deployment:** Fully containerized with **Docker**, ensuring environment parity between development and production NAS/Server environments.

---

## 📊 Analytics & Core Systems

### 🏗 Transactional Logic
- **Advanced P&L Reconstruction:** Real-time calculation of R:R (Risk/Reward) metrics across multiple timeframe layers (HTF/MTF/LTF).
- **Partial-Close Engine:** Sophisticated logic to scale out of positions while maintaining accurate cumulative P&L tracking.

### 📈 Quantitative Dashboard
- **Performance Modeling:** Automated analysis of win rates, median/average R:R, and Long/Short ratios.
- **Temporal Filtering:** Dynamic analysis across custom timeframes (Daily through Yearly) utilizing optimized SQL aggregation.

### 📚 Knowledge & Asset Management
- **Integrated Knowledge Base:** A dedicated internal library for technical documentation (PDF/Video/Image support).
- **Gallery Hub:** High-performance media gallery with infinite scroll and optimized image compression for chart analysis.

---

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













