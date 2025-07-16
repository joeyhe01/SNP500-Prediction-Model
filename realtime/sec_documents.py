#Author: Taaj Stillitano
#Date Created: 2025-07-01
#Date Updated: 2025-07-01
#Description: This module contains functions to query the U.S. Security and Exchange Comission's
#EDGAR API. The API will be queried through the datamule Python package.
#This entity is responsible for collecting, validating, and maintaining
#information about securities offerings and public companies. The API provides access to
#a wealth of data, including company filings, financial statements, and other
#disclosures required by law.

from datamule import Portfolio
import pandas as pd
import os

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

def get_documents(start_date:str, end_date:str, submission_types: list[str] = []):
    '''
    Query the SEC EDGAR API for company filings for a given date range and submission types.
    Save the documents in a "bronze" directory as TAR files.
    If no submission types are provided, default to common filings like '10-K', '10-Q', etc.

    INPUTS:
    -   start_date: str - The start date for the filings in 'YYYY-MM-DD' format.
    -   end_date: str - The end date for the filings in 'YYYY-MM-DD
    -   submission_types: list[str] - A list of submission types to filter the filings.
    If empty, defaults to common filings like '10-K', '10-Q', etc.
    
    OUTPUTS:
    -   None - The function saves the filings in the specified output directory.
    '''
    #If no submissions are passed then use the following default submission types
    #according to research these are the most useful filings for stock predictions
    #they deal with stocks, insider trading, and other important financial information
    if not submission_types:
        submission_types = ['10-K', '10-Q', '8-K', '4', '20-F', 'SC 13D', '13F-E']

    #check if data directory exists, if not create it
    #This is the parent directory where the data will be stored
    #it should be located at the same level as the code directory
    data_folder_path = os.path.abspath(os.path.join(os.getcwd(), '..\\data'))
    if not os.path.exists(data_folder_path):
        os.makedirs(data_folder_path)
    #check if bronze directory exists, if not create it
    output_directory = data_folder_path+"\\bronze" 
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Get the list of tickers
    tickers = get_tickers()

    # Initialize Portfolio by specifying output directory
    portfolio = Portfolio(path=output_directory)  
    # Pass dates as strings
    portfolio.download_submissions(
        filing_date=(start_date, end_date),
        submission_type=submission_types,
        ticker=tickers  # None means all tickers
    )

    print(f"Downloaded filings from {start_date} to {end_date} into '{output_directory}'")