import streamlit as st
import pandas as pd
import json
from datetime import datetime
import plotly.express as px
from data import load_data

def analyze_target_prices(filtered_df, trade_df, start_date, end_date, price_adjustment):
    # 날짜 필터링
    filtered_df = filtered_df[(filtered_df['createdAt'] >= start_date) & 
                             (filtered_df['createdAt'] <= end_date)]
    trade_df = trade_df[(trade_df['executedAt'] >= start_date) & 
                        (trade_df['executedAt'] <= end_date)]
    
    results = []
    matched_rates = []  # 매칭된 환율 데이터 저장
    for idx, trade_row in trade_df.iterrows():
        currency = trade_row['currencyCode0'] if trade_row['currencyCode'] == 'KRW' else trade_row['currencyCode']
        
        # 매수/매도에 따라 target_price 계산 (price_adjustment 적용)
        if trade_row['isBuyOrder'] == 1:  # 매수
            target_price = trade_row['price'] - price_adjustment
            # 매칭되는 환율 데이터 찾기
            matching_rates = filtered_df[
                (filtered_df['currencyCode'] == currency) & 
                (filtered_df['basePrice'] <= target_price)
            ]
        else:  # 매도
            target_price = trade_row['price'] + price_adjustment
            # 매칭되는 환율 데이터 찾기
            matching_rates = filtered_df[
                (filtered_df['currencyCode'] == currency) & 
                (filtered_df['basePrice'] >= target_price)
            ]
        
        matches = matching_rates.shape[0]
        
        # 매칭된 데이터가 있으면 저장
        if matches > 0:
            for _, rate_row in matching_rates.iterrows():
                matched_rates.append({
                    'currency': currency,
                    'basePrice': rate_row['basePrice'],
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
st.title('환율 목표가 분석')

# 데이터 로드
final_df, trade_df = load_data()

# 사이드바에 필터 추가
st.sidebar.header('분석 설정')

# 날짜 범위 선택
min_date = min(final_df['createdAt'].min(), trade_df['executedAt'].min())
max_date = max(final_df['createdAt'].max(), trade_df['executedAt'].max())

start_date = st.sidebar.date_input('시작일', min_date)
end_date = st.sidebar.date_input('종료일', max_date)

# 목표가 조정값 선택
price_adjustment = st.sidebar.slider('목표가 조정값', 0.1, 5.0, 1.0, 0.1)

# 통화 선택
available_currencies = ['USD', 'JPY', 'CNY', 'CAD']
selected_currencies = st.sidebar.multiselect('통화 선택', available_currencies, default=available_currencies)

# 통화 선택 후 데이터 필터링
filtered_trade_df = trade_df[
    trade_df.apply(lambda x: 
        (x['currencyCode0'] if x['currencyCode'] == 'KRW' else x['currencyCode']) in selected_currencies, 
        axis=1
    )
]
filtered_df = final_df[final_df['currencyCode'].isin(selected_currencies)]

# 분석 실행
start_datetime = datetime.combine(start_date, datetime.min.time())
end_datetime = datetime.combine(end_date, datetime.max.time())

results_df, matched_rates_df = analyze_target_prices(filtered_df, filtered_trade_df, start_datetime, end_datetime, price_adjustment)

# 결과 표시
st.header('분석 결과')

# 전체 통계
col1, col2, col3 = st.columns(3)
with col1:
    st.metric('전체 거래 수', len(results_df))
with col2:
    st.metric('목표가 도달 거래 수', results_df['found'].sum())
with col3:
    success_rate = (results_df['found'].sum() / len(results_df)) * 100
    st.metric('목표가 도달률', f'{success_rate:.2f}%')

# 통화별 분석
st.subheader('통화별 분석')
currency_analysis = results_df.groupby('currency').agg({
    'found': ['count', 'sum'],
    'match_count': 'sum'
}).round(2)
currency_analysis.columns = ['전체 거래', '목표가 도달', '총 매칭 횟수']
st.dataframe(currency_analysis)

# 시각화
st.subheader('시계열 분석')
time_series = results_df.set_index('executedAt')['found'].rolling('1D').mean()
fig = px.line(time_series, title='일별 목표가 도달률')
st.plotly_chart(fig)

# 거래 데이터 표시
st.subheader('거래 데이터')
st.dataframe(filtered_trade_df)

# 목표가 도달 데이터 표시
if not matched_rates_df.empty:
    st.subheader('목표가 도달 데이터')
    # 시간순으로 정렬
    matched_rates_df = matched_rates_df.sort_values(['currency', 'createdAt'])
    st.dataframe(matched_rates_df)
else:
    st.warning('선택한 기간 동안 목표가에 도달한 데이터가 없습니다.')

# 환율 데이터 표시
st.subheader('전체 환율 데이터')
st.dataframe(filtered_df)