import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go


def analyze_target_prices(filtered_df, trade_df, start_date, end_date, buy_price_adjustment, sell_price_adjustment, date_window):
    # 날짜 필터링
    filtered_df = filtered_df[(filtered_df['createdAt'] >= start_date) & 
                             (filtered_df['createdAt'] <= end_date + timedelta(days=date_window))]
    trade_df = trade_df[(trade_df['executedAt'] >= start_date) & 
                        (trade_df['executedAt'] <= end_date)]
    
    results = [] # 거래 결과에 대한 정보 저장
    matched_rates = []  # 매칭된 환율 데이터 저장

    for idx, trade_row in trade_df.iterrows():
        currency = trade_row['currencyCode0'] if trade_row['currencyCode'] == 'KRW' else trade_row['currencyCode']
        trade_date = trade_row['executedAt']
        # 매수/매도에 따라 target_price 계산 (price_adjustment 적용)
        if trade_row['isBuyOrder'] == 1:  # 매수
            target_price = trade_row['price'] - buy_price_adjustment
            # 매칭 조건: target_price 이하
            matching_rates = filtered_df[
                (filtered_df['currencyCode'] == currency) & 
                (filtered_df['basePrice'] <= target_price) &
                (filtered_df['createdAt'].between(trade_date, trade_date + timedelta(days=date_window)))
            ]
         
        else:  # 매도
            target_price = trade_row['price'] + sell_price_adjustment
            # 매칭 조건: target_price 이상
            matching_rates = filtered_df[
                (filtered_df['currencyCode'] == currency) & 
                (filtered_df['basePrice'] >= target_price) &
                (filtered_df['createdAt'].between(trade_date, trade_date + timedelta(days=date_window)))
            ]
        
        matches = matching_rates.shape[0]
        if currency == 'JPY':
            trade_row['amount'] = trade_row['amount'] // 100
        # 매칭된 데이터가 있으면 저장
        if matches > 0:
            for _, rate_row in matching_rates.iterrows():
                matched_rates.append({
                    'currency': currency,
                    'basePrice': rate_row['basePrice'],
                    'createdAt': rate_row['createdAt'],
                    'trade_executedAt': trade_row['executedAt'],
                    'trade_price': trade_row['price'],
                    'amount' : trade_row['amount'],
                    'order_type': '매수' if trade_row['isBuyOrder'] == 1 else '매도'
                })
        
        results.append({
            'currency': currency,
            'order_type': '매수' if trade_row['isBuyOrder'] == 1 else '매도',
            'original_price': trade_row['price'],
            'target_price': target_price,
            'found': matches > 0,
            'match_count': matches,
            'amount' : trade_row['amount'],
            'executedAt': trade_row['executedAt']
        })
    
    return pd.DataFrame(results), pd.DataFrame(matched_rates)

@st.cache_data
# 수익 계산 함수
def calculate_profit(results_df, adjustment, start_date, end_date, date_window):
    # start_date와 end_date를 datetime64[ns]로 변환
    start_datetime = pd.to_datetime(start_date)
    end_datetime = pd.to_datetime(end_date)
    
    # 'found'가 True인 경우에만 수익 계산
    profit_df = results_df[
        (results_df['executedAt'] >= start_datetime) &
        (results_df['executedAt'] <= end_datetime + timedelta(days=date_window)) &
        (results_df['found'] == True)
    ]
    # 🔹 중복 제거 (같은 시간, 통화, 금액이 중복된 거래 제거)
    profit_df = profit_df.drop_duplicates(subset=['currency', 'executedAt', 'amount'])
    # 매수와 매도에 따른 수익 계산
    # 매수와 매도 데이터 복사본 생성
    buy_profit_df = profit_df[profit_df['order_type'] == '매수'].copy()
    sell_profit_df = profit_df[profit_df['order_type'] == '매도'].copy()
    
    buy_profit_df['profit'] = buy_profit_df['amount'] * adjustment
    sell_profit_df['profit'] = sell_profit_df['amount'] * adjustment
    
    total_buy_amo = buy_profit_df['amount'].sum()
    total_buy_pro = buy_profit_df['profit'].sum()
    
    total_sell_amo = sell_profit_df['amount'].sum()
    total_sell_pro = sell_profit_df['profit'].sum()
    
    return (buy_profit_df, total_buy_amo, total_buy_pro), (sell_profit_df, total_sell_amo, total_sell_pro)

def display_metrics(results_df, buy_results_df, sell_results_df, adjustment, total_buy_amo, total_buy_pro, total_sell_amo, total_sell_pro):
    # 메트릭 표시 함수
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)
    col7, col8, col9 = st.columns(3)
    with col1:
        st.metric('전체 거래 수', len(results_df))
    with col2:
        total_found = results_df['found'].sum()
        st.metric('목표가 도달 거래 수', total_found)
    with col3:
        total_buy_results = buy_results_df['found'].sum()
        total_sell_results = sell_results_df['found'].sum()
        st.metric('매수/매도 목표가 도달 거래 수', f'{int(total_buy_results), int(total_sell_results)}')
    with col4:
        st.metric('현재 조정값', adjustment)
    with col5:
        st.metric('매수 수익', f'{int(total_buy_pro):,}')   
    with col6:
        st.metric('매도 수익', f'{int(total_sell_pro):,}')  
    with col7:
        total_success_rate = (total_found / len(results_df)) * 100 if len(results_df) > 0 else 0
        st.metric('목표가 도달률', f'{total_success_rate:.2f}%')

    with col8:
        st.metric('총 거래량', f'{int(total_buy_amo + total_sell_amo):,}')
    with col9:
        st.metric('총 수익', f'{int(total_buy_pro + total_sell_pro):,}')            

# 수익률 변화 시각화
def plot_profit_over_time(profit_df, title):
    profit_df['date'] = profit_df['executedAt'].dt.date  # 날짜 단위로 그룹화
    daily_profit = profit_df.groupby(['date', 'order_type'])['amount'].sum().reset_index()
    
    fig = px.line(
        daily_profit, 
        x='date', 
        y='amount', 
        color='order_type',
        title=title,
        labels={"amount": "Profit Amount", "date": "Date"}
    )
    st.plotly_chart(fig)

import pandas as pd
import plotly.express as px
import streamlit as st

# 매칭 성공률 파이차트
def plot_matching_success(results_df, title):
    # 만약 'narwhals' 데이터프레임이라면 pandas로 변환
    if isinstance(results_df, pd.DataFrame) is False:
        results_df = results_df.to_pandas()

    found_counts = results_df['found'].value_counts().reset_index()
    found_counts.columns = ['found', 'count']
    found_counts['found'] = found_counts['found'].map({True: 'Matched', False: 'Not Matched'})
    fig = px.pie(
        found_counts, 
        values='count', 
        names='found', 
        title=title,
    )

    st.plotly_chart(fig)


