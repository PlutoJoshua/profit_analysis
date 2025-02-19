import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from data import load_trade_data, load_yh_data
from st_aggrid import AgGrid # pip install streamlit-aggrid

# 예시로 거래 데이터와 야후 데이터 로드
trade_df = load_trade_data()  # 거래 데이터 로드
final_df = load_yh_data()     # 야후 데이터 로드

def analyze_target_prices(filtered_df, trade_df, buy_price_adjustment, sell_price_adjustment, date_window):

    results = []
    matched_rates = []
    for idx, trade_row in trade_df.iterrows():
        currency = trade_row['currencyCode0'] if trade_row['currencyCode'] == 'KRW' else trade_row['currencyCode']
        trade_date = trade_row['executedAt']

        # 거래 날짜를 기준으로 환율 데이터 기간 설정
        start_date = trade_date
        end_date = trade_date + timedelta(days=date_window)

        # 매수/매도에 따라 target_price 계산
        if trade_row['isBuyOrder'] == 1:  # 매수
            target_price = trade_row['price'] - buy_price_adjustment
            matching_rates = filtered_df[
                (filtered_df['currencyCode'] == currency) &
                ((filtered_df['low'] <= target_price) | (filtered_df['high'] >= target_price)) &
                (filtered_df['Date'] >= start_date) &
                (filtered_df['Date'] <= end_date)  # 거래 날짜부터 date_window 기간까지
            ]
        else:  # 매도
            target_price = trade_row['price'] + sell_price_adjustment
            matching_rates = filtered_df[
                (filtered_df['currencyCode'] == currency) &
                ((filtered_df['low'] <= target_price) | (filtered_df['high'] >= target_price)) & 
                (filtered_df['Date'] >= start_date) &
                (filtered_df['Date'] <= end_date)  # 거래 날짜부터 date_window 기간까지
            ]

        matches = matching_rates.shape[0]

        # 매칭된 데이터 저장
        if matches > 0:
            for _, rate_row in matching_rates.iterrows():
                matched_rates.append({
                    'currency': currency,
                    'order_type': '매수' if trade_row['isBuyOrder'] == 1 else '매도',
                    'trade_price': trade_row['price'],
                    'highPrice' : rate_row['high'],
                    'LowPrice' :rate_row['low'],
                    'basePrice': rate_row['close'],
                    'trade_executedAt': trade_row['executedAt'],
                    'createdAt': rate_row['Date'],
                })

        results.append({
            'currency': currency,
            'order_type': '매수' if trade_row['isBuyOrder'] == 1 else '매도',
            'original_price': trade_row['price'],
            'target_price': target_price,
            'found': matches > 0,
            'match_count': matches,
            'executedAt': trade_row['executedAt'],
        })

    return pd.DataFrame(results), pd.DataFrame(matched_rates)

# 날짜 범위 선택
# min_date = min(final_df['createdAt'].min(), trade_df['executedAt'].min())
max_date = max(final_df['Date'].max(), trade_df['executedAt'].max())
# 가장 최근 날짜 기준 일주일 전 계산
one_week_ago = max_date - timedelta(days=7)

start_date = pd.Timestamp(st.sidebar.date_input('시작일', one_week_ago))
end_date = pd.Timestamp(st.sidebar.date_input('종료일', max_date))

# 목표가 조정값 선택

buy_price_adjustment = st.sidebar.slider('매수 목표가 조정값', 0.0, 10.0, 1.0, 0.5)
sell_price_adjustment = st.sidebar.slider('매도 목표가 조정값', 0.0, 10.0, 1.0, 0.5)

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

# Streamlit 앱 메인
st.title('환율 목표가 분석 (야후 파이낸스)')

# 분석 실행
filtered_trade_df = filtered_trade_df[
    (filtered_trade_df['executedAt'] >= start_date) & 
    (filtered_trade_df['executedAt'] <= end_date)
]
filtered_df = filtered_df[
    (filtered_df['Date'] >= start_date)
]

date_window = st.sidebar.slider('환율 분석 기간(일)', 1, 30, 5)

# 분석 실행
results_df, matched_rates_df = analyze_target_prices(filtered_df, filtered_trade_df, buy_price_adjustment, sell_price_adjustment, date_window)

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
    matched_rates_df['time_diff'] = matched_rates_df['trade_executedAt'] - matched_rates_df['createdAt']
    st.dataframe(matched_rates_df)
else:
    st.warning('선택한 기간 동안 목표가에 도달한 데이터가 없습니다.')

    # Ag-Grid 테이블을 사용하여 데이터 시각화
AgGrid(matched_rates_df, editable=True, filter=True, sortable=True, resizable=True)

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

# 시계열 차트 작성 함수 (매수와 매도 차트를 나눠서 생성)
def plot_buy_time_series(df, currency):
    # 매수 데이터만 필터링
    buy_df = df[(df['currency'] == currency) & (df['order_type'] == '매수')]
    
    fig = px.line()
    
    # 매수 고가, 저가, 거래 가격
    fig.add_scatter(x=buy_df['createdAt'], 
                    y=buy_df['highPrice'], 
                    mode='lines', 
                    name=f'{currency} 매수 고가', 
                    line=dict(color='green'))
    fig.add_scatter(x=buy_df['createdAt'], 
                    y=buy_df['LowPrice'], 
                    mode='lines', 
                    name=f'{currency} 매수 저가', 
                    line=dict(color='red'))
    fig.add_scatter(x=buy_df['createdAt'], 
                    y=buy_df['trade_price'], 
                    mode='lines', 
                    name=f'{currency} 매수 거래 가격', 
                    line=dict(color='blue'))
    
    fig.update_layout(
        title=f'{currency} 매수 시계열 차트',
        xaxis_title='날짜',
        yaxis_title='가격',
        legend_title='데이터 타입'
    )
    return fig

def plot_sell_time_series(df, currency):
    # 매도 데이터만 필터링
    sell_df = df[(df['currency'] == currency) & (df['order_type'] == '매도')]
    
    fig = px.line()
    
    # 매도 고가, 저가, 거래 가격
    fig.add_scatter(x=sell_df['createdAt'], 
                    y=sell_df['highPrice'], 
                    mode='lines', 
                    name=f'{currency} 매도 고가', 
                    line=dict(color='orange'))
    fig.add_scatter(x=sell_df['createdAt'], 
                    y=sell_df['LowPrice'], 
                    mode='lines', 
                    name=f'{currency} 매도 저가', 
                    line=dict(color='purple'))
    fig.add_scatter(x=sell_df['createdAt'], 
                    y=sell_df['trade_price'], 
                    mode='lines', 
                    name=f'{currency} 매도 거래 가격', 
                    line=dict(color='black'))
    
    fig.update_layout(
        title=f'{currency} 매도 시계열 차트',
        xaxis_title='날짜',
        yaxis_title='가격',
        legend_title='데이터 타입'
    )
    return fig

# 목표가 도달 데이터
if not matched_rates_df.empty:
    st.subheader('목표가 도달 데이터 시계열')

    # 날짜 순으로 정렬
    matched_rates_df = matched_rates_df.sort_values(['currency', 'createdAt'])
    
    # 통화별로 매수 시계열 차트 생성
    for currency in matched_rates_df['currency'].unique():
        # 매수 차트
        fig_buy = plot_buy_time_series(matched_rates_df, currency)
        st.plotly_chart(fig_buy)
        
        # 매도 차트
        fig_sell = plot_sell_time_series(matched_rates_df, currency)
        st.plotly_chart(fig_sell)

else:
    st.warning('선택한 기간 동안 목표가에 도달한 데이터가 없습니다.')
