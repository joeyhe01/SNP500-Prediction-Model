import pandas as pd
from sqlalchemy import text as sa_text
from sentence_transformers import SentenceTransformer
from database import SECFilings, get_db_session

model = SentenceTransformer('all-MiniLM-L6-v2')

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
    # Ensure all tickers are uppercase
    tickers_ciks = {ticker.upper(): cik for ticker, cik in tickers_ciks.items()}
    #Make sure CIKs are strings
    tickers_ciks = {ticker: f"{int(cik):010d}" for ticker, cik in tickers_ciks.items()}

    return tickers_ciks

def get_latest_matching_chunks(ticker: str, sentiment: str, top_k=5):
    '''
    Query the vector database for SEC filing CHUNKS for the relevant tickers.
    Function expects the following format:
    [
        {"ticker": "AAPL", "sentiment": "positive"},
        {"ticker": "GOOGL", "sentiment": "negative"}
    ]

    INPUTS:
    -   ticker: The stock ticker symbol (e.g., "AAPL")
    -   sentiment: The sentiment to filter by (e.g., "positive" or "negative")
    -   top_k: The number of top results to return (default is 5)

    OUTPUTS:
    -   List of matching SEC filing chunks:
    '''
    #Initialize the database session
    session = get_db_session()

    #get a dictionary of abbreviated tickers to CIK mappings from wiki
    ticker_cik_dict = get_tickers()
    #format the CIKs as 10 digit strings to match the SEC filing format in vector database
    cik = str(ticker_cik_dict.get(ticker.upper()))

    #
    search_query = f"{ticker} {sentiment}"
    query_vector = model.encode(search_query).tolist()

    #sql query
    #perform vector similarity serach taking the cosine between the 
    #input vector and embedding vectors in the database
    sql = sa_text("""
        SELECT *
        FROM sec_filings
        WHERE cik = :cik
        ORDER BY filing_date DESC,
                 embedding <#> (:embedding)::vector
        LIMIT :top_k
    """)

    #format the result output into dictionary
    results = session.execute(sql, {
        "cik": cik,
        "embedding": query_vector,
        "top_k": top_k
    }).mappings().all()

    return results

def rag_query_pipeline(query_inputs):
    '''
    Query the RAG model for relevant SEC filing chunks based on user queries.
    INPUTS:
    -   query_inputs: List of dictionaries with keys "ticker" and "sentiment"
    OUTPUTS:
    -   List of dictionaries with matched SEC filing chunks for each query
    '''
    #initlaize reponse list
    all_responses = []

    #go through all ticker:sentiment input queries
    for query in query_inputs:
        #format ticker name for matching
        ticker = query.get("ticker", "").upper()
        sentiment = query.get("sentiment", "")

        print(f"🔍 Querying SEC filings for {ticker} ({sentiment})...")
        #perform vector similarity cosine search
        matches = get_latest_matching_chunks(ticker, sentiment, top_k=5)

        match_snippets = [
            {
                "chunk_id": row["chunk_id"],
                "filing_date": row["filing_date"],
                "text_snippet": row["text"][:500] + "..."
            } for row in matches
        ]

        all_responses.append({
            "ticker": ticker,
            "sentiment": sentiment,
            "matches": match_snippets
        })

    return all_responses

#sample code to test
#assumed input from llm_sentiment_model.py
if __name__ == "__main__":

    query_input = [
        {"ticker": "AAPL", "sentiment": "positive"},
        {"ticker": "GOOGL", "sentiment": "negative"}
    ]

    results = rag_query_pipeline(query_input)

    for r in results:
        print(f"\n📘 {r['ticker']} ({r['sentiment']})")
        for match in r['matches']:
            print(f"• [Date: {match['filing_date']}] {match['text_snippet'][:200]}...")
