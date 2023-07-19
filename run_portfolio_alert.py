from portfolio_functions import run_portfolio_alert_algorithm

portfolio_file = 'portfolio.txt'
target_portfolio_file = 'target_portfolio.txt'
email_details_file = 'email_details.txt'
# email_details_file = None
run_portfolio_alert_algorithm(target_portfolio_file, portfolio_file, email_details_file)
