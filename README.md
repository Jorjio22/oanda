OANDA Forex Trading Automation
A Python-based project for automating forex trading using the OANDA v20 REST API, Selenium for web scraping, and Django for data visualization. The system collects and analyzes market data, storing metrics like prices, volatility, and volume in a PostgreSQL database, with a Django admin panel for management. Designed for future integration with AI for predictive trading.
Features

Fetches historical candlestick data and real-time market data via OANDA API
Parses additional web data using Selenium (e.g., market trends or external metrics)
Calculates trading metrics:
Open, high, low, close prices
Absolute and percentage volatility (open/low)
Volume start/stop, delta, percent change, and average per minute
Number of price changes, max/min/average delays


Stores data in PostgreSQL for efficient querying
Django admin panel for data visualization and management
Prepared for AI integration for predictive trading models

Technologies

Python
OANDAPyV20
Selenium
Django
PostgreSQL
REST API

How to Run

Clone the repository: git clone https://github.com/Jorjio22/oanda.git
Install dependencies: pip install -r requirements.txt
Configure oanda.cfg with your OANDA API token and account ID
Set up PostgreSQL database and update Django settings
Run migrations: python manage.py migrate
Start the Django server: python manage.py runserver
Run the main script: python main.py

Example Output

CSV file with parsed market data (e.g., EUR/USD prices, volatility)
Django admin panel displaying trading metrics
Database tables storing all calculated parameters

Notes

Ensure you have a valid OANDA API token
Selenium requires a compatible web driver (e.g., ChromeDriver)
Project is designed for extensibility with AI/ML models

