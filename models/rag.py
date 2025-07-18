import pandas as pd


#sample RAG input
#[
#  {{"ticker": "AAPL", "sentiment": "positive"}},
#  {{"ticker": "GOOGL", "sentiment": "negative"}}
#]

def get_tickers() -> dict[str, str]:
    '''
    Scrap wikipedia page to get the current S&P 500 tickers and their CIKs.
    Returns a dictionary with tickers as keys and CIKs as values.
    Replace '.' with '-' to match the format used in SEC filings.

    INPUTS:
    -   None

    OUTPUTS:
    -   dict[str, str] - A dictionary mapping tickers to CIKs.
    '''

    # Define the URL for the S&P 500 companies list
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tables = pd.read_html(url)
    df = tables[0]
    
    # Create a dictionary mapping tickers to CIKs
    tickers_ciks = dict(zip(df['Symbol'].str.replace('.', '-'), df['CIK']))
    
    return tickers_ciks