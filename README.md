# portfolio_alert

A portfolio with multiple positions can be rebalanced with some frequency (e.g. monthly or quartely), or when the weights of the positions exceed some predetermined tolerance value. This code aims to help with the second case. 

Monitor your portfolio weights vs some target weights and alert by email if rebalancing is required.
- Currently only supports positions denoted in USD and that can be accessed with the yfinance python package (stock names as in Yahoo Finance).
- Cash is also a valid position.
- Positions can have two types "rebalanced" or "minimal_weight". 
- The minimal_weight positions must be less that 100%, and the rebalanced positions need to add up to 100% (relative to what is left apart from the minimal_weight portion of the portfolio).
- The tolerance is given in percents. Meaning, if any position weight exceeds its target weight by that amount of percents, a rebalancing alert is triggered.


Example for a valid "target_portfolio.txt" input file with two "minimal_weight" positions and three "rebalanced" positions:
```
    tolerance 5%
    BRK-B >4%
    GME >2%
    VOO 45%
    TLT 45%
    cash 10%
```
