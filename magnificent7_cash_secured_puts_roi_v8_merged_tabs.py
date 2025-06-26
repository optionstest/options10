
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

def fmt(x):
    return f"{x:.2f}" if isinstance(x, (float, int)) else x

def get_weekly_expirations(n=10):
    today = datetime.today()
    expirations = []
    for i in range(n):
        friday = today + timedelta((4 - today.weekday()) % 7 + i * 7)
        expirations.append(friday.strftime("%Y-%m-%d"))
    return expirations

# Page configuration and disclaimer
st.set_page_config(layout="wide", page_title="Options Analyzer")
with st.expander("📌 Disclaimer", expanded=True):
    st.markdown("""
    **This tool does not provide financial advice.**

    It is not intended to offer personalized investment recommendations, predict market movements, or suggest specific actions like buying or selling securities. 

    The data and insights presented are based on public sources (e.g., Yahoo Finance) and are provided for **educational and analytical purposes only**.

    Always conduct your own research or consult with a licensed financial advisor before making investment decisions.
    """)

st.title("📊 Options Analyzer for Cash Secured Puts, Covered Calls & Investing Lists")

tab1, tab2, tab3 = st.tabs(["💰 Cash Secured Put", "📈 Covered Call", "📋 Investing-lists"])

# CSP and CC Tabs
def render_tab(strategy, tab, key_suffix):
    with tab:
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            min_price = st.number_input("Min Price", min_value=0.0, value=50.0, key=f"min_price_{key_suffix}")
        with col2:
            max_price = st.number_input("Max Price", min_value=min_price, value=500.0, key=f"max_price_{key_suffix}")
        with col3:
            moneyness_pct = st.slider("Moneyness %", 1, 100, 10, key=f"moneyness_{key_suffix}")
        with col4:
            expiration_list = get_weekly_expirations(8)
        with col5:
            additional_tickers = st.text_input("Add tickers (comma separated)", "", key=f"additional_{key_suffix}")
        with col6:
            default_tickers = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "SPY", "QQQ"]
            if additional_tickers:
                default_tickers += [t.strip().upper() for t in additional_tickers.split(",")]
            tickers_list = ["ALL"] + sorted(set(default_tickers))
            selected_stock = st.selectbox("Select Ticker or 'ALL'", tickers_list, key=f"ticker_{key_suffix}")

        def analyze_options(ticker):
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                hist = stock.history(period="5d")
                current_price = hist["Close"].iloc[-1]
                if current_price < min_price or current_price > max_price:
                    return []

                options_data = []
                for expiration in expiration_list:
                    try:
                        opt_chain = stock.option_chain(expiration)
                        options = opt_chain.puts if strategy == "Cash Secured Put" else opt_chain.calls
                        target_strike = current_price * (1 - moneyness_pct / 100) if strategy == "Cash Secured Put" else current_price * (1 + moneyness_pct / 100)
                        options_filtered = options[options["strike"] <= target_strike] if strategy == "Cash Secured Put" else options[options["strike"] >= target_strike]
                        if options_filtered.empty:
                            continue
                        selected = options_filtered.iloc[-1] if strategy == "Cash Secured Put" else options_filtered.iloc[0]
                        strike_price = selected["strike"]
                        premium = (selected["bid"] + selected["ask"]) / 2 if selected["bid"] and selected["ask"] else selected["lastPrice"]
                        days_to_exp = (datetime.strptime(expiration, "%Y-%m-%d") - datetime.today()).days
                        abs_roi = premium / strike_price * 100
                        ann_roi = (abs_roi / days_to_exp) * 365 if days_to_exp > 0 else 0

                        row = {
                            "Ticker": ticker,
                            "Strategy": strategy,
                            "Current Price": fmt(current_price),
                            "Strike Price": fmt(strike_price),
                            "Premium": fmt(premium),
                            "Days to Exp": days_to_exp,
                            "Expiration": expiration,
                            "Ann ROI (%)": fmt(ann_roi),
                            "Abs ROI (%)": fmt(abs_roi)
                        }
                        options_data.append(row)
                    except:
                        continue
                return options_data
            except:
                return []

        tickers_to_process = sorted(set(default_tickers)) if selected_stock == "ALL" else [selected_stock]
        all_results = []
        for tkr in tickers_to_process:
            results = analyze_options(tkr)
            all_results.extend(results)

        if all_results:
            df = pd.DataFrame(all_results)
            df = df.sort_values(by="Ann ROI (%)", ascending=False)
            st.dataframe(df, use_container_width=True)
            fig = px.bar(df, x="Expiration", y="Ann ROI (%)", color="Ticker", barmode="group")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data found.")

# Render CSP and CC tabs
render_tab("Cash Secured Put", tab1, "csp")
render_tab("Covered Call", tab2, "cc")

# Investing Lists Tab
with tab3:
    nasdaq_wide_moat = [
        "AAPL", "MSFT", "GOOGL", "META", "ADBE", "COST", "NVDA", "MA", "V", "INTU",
        "TXN", "TMO", "SBUX", "MDT", "CSCO", "LRCX", "QCOM", "PYPL", "ISRG", "AMZN"
    ]
    nasdaq_high_quality = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "COST", "ADBE", "PEP", "AVGO",
        "LIN", "WMT", "MRK", "ORCL", "CRM", "NKE", "INTU", "TXN", "QCOM", "MDT"
    ]
    st.subheader("📋 Explore High Quality and Wide Moat Companies")
    list_choice = st.selectbox("Choose a list", ["Nasdaq Wide Moat", "High Quality"])
    stock_list = nasdaq_wide_moat if list_choice == "Nasdaq Wide Moat" else nasdaq_high_quality
    pct_from_high = st.slider("Max % below 52-week high", 0, 100, 20)
    pct_from_low = st.slider("Max % above 52-week low", 0, 100, 20)

    data = []
    for ticker in stock_list:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="1y")
            if hist.empty: continue
            curr_price = hist["Close"][-1]
            wk_52_high = hist["Close"].max()
            wk_52_low = hist["Close"].min()
            if curr_price > wk_52_high * (1 - pct_from_high / 100) or curr_price < wk_52_low * (1 + pct_from_low / 100):
                continue
            data.append({
                "Symbol": ticker,
                "Company Name": info.get("shortName", "N/A"),
                "Price": fmt(curr_price),
                "Market Cap": info.get("marketCap", "N/A"),
                "Quality Percentile": info.get("overallRisk", "N/A"),
                "ROE": fmt(info.get("returnOnEquity", 0.0) * 100),
                "Return On Capital": fmt(info.get("returnOnAssets", 0.0) * 100),
                "Profit Margin": fmt(info.get("profitMargins", 0.0) * 100),
                "52W Low": fmt(wk_52_low),
                "52W High": fmt(wk_52_high)
            })
        except:
            continue

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
