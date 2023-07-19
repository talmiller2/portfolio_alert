# portfolio_alert

Rebalancing a portfolio based on target weights can be done with some frequency (e.g. monthly or quartely), or actively based on a deviation of the portfolio weights from the target weights. This code is designed for the latter, but can trivially be also used for the former.  

The run_portfolio_alert.py script monitors your portfolio (instantly or daily as a cron job), and alerts by email if rebalancing is required, while also giving the exact rebalancing instructions.
This directory needs to contain the files:
- email_details.txt: Details to the email (if none then will print to screen).
- portfolio.txt: Log the status of the portfolio positions for different dates. The code will update the portfolio as it changes with time. Only the last line is relavant for the code.
- target_portfolio.txt: Define the target weights of the portfolio and the tolerance % for rebalancing.

Notes:
- Currently only supports positions denoted in USD and that can be accessed with the yfinance python package (stock names as they appear in Yahoo Finance).
- Cash is also a valid position.
- Positions can have two types "rebalanced" or "minimal_weight". 
- The minimal_weight positions must sum to less than 100%, and the rebalanced positions need to add up to exactly 100% (relative to what is left apart from the minimal_weight portion of the portfolio).
- The tolerance is given in percents. Meaning, if any position weight exceeds its target weight by that amount of percents, a rebalancing alert is triggered.

Example input files are in the example_files directory.
