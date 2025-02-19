import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta

def load_yahoo_data(currencies, start_date, end_date):
    """
    야후 파이낸스에서 통화 데이터를 다운로드합니다.
    """
    data_frames = []
    for currency in currencies:
        ticker = f'{currency}=X'
        df = yf.download(ticker, start=start_date, end=end_date)
        df['currency'] = currency
        df.reset_index(inplace=True)
        df.rename(columns={
            'Date': 'createdAt',
            'High': 'highPrice',
            'Low': 'lowPrice',
            'Close': 'closePrice'
        }, inplace=True)
        data_frames.append(df)
    return pd.concat(data_frames, ignore_index=True)

def analyze_target_prices(filtered_df, trade_df, buy_price_adjustment, sell_price_adjustment):
    results = []
    matched_rates = []
    for idx, trade_row in trade_df.iterrows():
        currency = trade_row['currencyCode0'] if trade_row['currencyCode'] == 'KRW' else trade_row['currencyCode']

        # 매수/매도에 따라 target_price 계산
        if trade_row['isBuyOrder'] == 1:  # 매수
            target_price = trade_row['price'] - buy_price_adjustment
            # 목표가가 고가와 저가 사이에 있는 경우
            matching_rates = filtered_df[
                (filtered_df['currency'] == currency) &
                (filtered_df['lowPrice'] <= target_price) &
                (filtered_df['highPrice'] >= target_price)
            ]
        else:  # 매도
            target_price = trade_row['price'] + sell_price_adjustment
            # 목표가가 고가와 저가 사이에 있는 경우
            matching_rates = filtered_df[
                (filtered_df['currency'] == currency) &
                (filtered_df['lowPrice'] <= target_price) &
                (filtered_df['highPrice'] >= target_price)
            ]

        matches = matching_rates.shape[0]

        # 매칭된 데이터 저장
        if matches > 0:
            for _, rate_row in matching_rates.iterrows():
                matched_rates.append({
                    'currency': currency,
                    'basePrice': rate_row['closePrice'],
                    'createdAt': rate_row['createdAt'],
                    'trade_executedAt': trade_row['executedAt'],
                    'trade_price': trade_row['price'],
                    'order_type': '매수' if trade_row['isBuyOrder'] == 1 else '매도'
                })

        results.append({
            'currency': currency,
            'order_type': '매수' if trade_row['isBuyOrder'] == 1 else '매도',
            'original_price': trade_row['price'],
            'target_price': target_price,
            'found': matches > 0,
            'match_count': matches,
            'executedAt': trade_row['executedAt']
        })

    return pd.DataFrame(results), pd.DataFrame(matched_rates)

# Streamlit 앱 메인
st.title('환율 목표가 분석 (야후 파이낸스)')

# 설정: 2024-08 ~ 2025-02
start_date = '2024-08-01'
end_date = '2025-02-28'

# 사용자 입력 설정
st.sidebar.header('분석 설정')
buy_price_adjustment = st.sidebar.slider('매수 목표가 조정값', 0.1, 10.0, 1.0, 0.1)
sell_price_adjustment = st.sidebar.slider('매도 목표가 조정값', 0.1, 10.0, 1.0, 0.1)

available_currencies = ['USD', 'JPY', 'CNY', 'CAD']
selected_currencies = st.sidebar.multiselect('통화 선택', available_currencies, default=available_currencies)

# 야후 파이낸스 데이터 로드
final_df = load_yahoo_data(selected_currencies, start_date, end_date)

# 거래 데이터 (예제 데이터)
trade_data = {
    'currencyCode': ['USD', 'JPY', 'CNY', 'CAD'],
    'currencyCode0': ['KRW', 'KRW', 'KRW', 'KRW'],
    'price': [1300, 9.5, 200, 1000],
    'isBuyOrder': [1, 0, 1, 0],
    'executedAt': [datetime(2025, 2, 1), datetime(2025, 2, 2), datetime(2025, 1, 15), datetime(2025, 1, 20)]
}
trade_df = pd.DataFrame(trade_data)

# 분석 실행
results_df, matched_rates_df = analyze_target_prices(final_df, trade_df, buy_price_adjustment, sell_price_adjustment)

# 결과 표시
st.header('분석 결과')
st.metric('전체 거래 수', len(results_df))
st.metric('목표가 도달 거래 수', results_df['found'].sum())
success_rate = (results_df['found'].sum() / len(results_df)) * 100
st.metric('목표가 도달률', f'{success_rate:.2f}%')

# 통화별 분석 결과 표시
st.subheader('통화별 목표가 도달 거래 수')
currency_analysis = results_df.groupby(['currency', 'order_type']).agg({
    'found': ['count', 'sum'],
    'match_count': 'sum'
}).round(2)
currency_analysis.columns = ['전체 거래', '목표가 도달', '총 매칭 횟수']
currency_analysis = currency_analysis.reset_index()
st.dataframe(currency_analysis)

# 매수와 매도에 대한 바 차트 시각화
st.subheader('매수 및 매도 목표가 도달 거래 수 바 차트')
fig_bar = px.bar(currency_analysis, 
                  x='currency', 
                  y='목표가 도달', 
                  color='order_type', 
                  title='통화별 매수 및 매도 목표가 도달 거래 수',
                  labels={'목표가 도달': '목표가 도달 거래 수', 'currency': '통화'})
st.plotly_chart(fig_bar)

# 목표가 도달 데이터 표시
if not matched_rates_df.empty:
    st.subheader('목표가 도달 데이터')
    matched_rates_df = matched_rates_df.sort_values(['currency', 'createdAt'])
    st.dataframe(matched_rates_df)
else:
    st.warning('선택한 기간 동안 목표가에 도달한 데이터가 없습니다.')

# 환율 데이터 표시
st.subheader('전체 환율 데이터')
st.dataframe(final_df)
