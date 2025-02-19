import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta
from data import load_trade_data, load_yh_data
from st_aggrid import AgGrid

# 데이터 로드
trade_df = load_trade_data()
final_df = load_yh_data()

# 목표가 분석 함수
def analyze_target_prices(filtered_df, trade_df, buy_price_adjustment, sell_price_adjustment, date_window):
    results, matched_rates = [], []

    for _, trade_row in trade_df.iterrows():
        # 원화 > 외화 코드 변환
        currency = trade_row['currencyCode0'] if trade_row['currencyCode'] == 'KRW' else trade_row['currencyCode']

        trade_date, is_buy_order, trade_price = trade_row['executedAt'], trade_row['isBuyOrder'], trade_row['price']
        # 매수/매도 목표 가격 설정
        target_price = trade_price - buy_price_adjustment if is_buy_order else trade_price + sell_price_adjustment

        # 매칭 조건
        # 1. 통화코드 일치
        # 2. 저가 보다 높거나 같음
        # 3. 고가 보다 작거나 같음
        # 4. 환율 데이터 날짜는 거래 날짜부터 date_window까지

        matching_rates = filtered_df[(filtered_df['currencyCode'] == currency) &
                                     (filtered_df['low'] <= target_price) &
                                     (filtered_df['high'] >= target_price) &
                                     (filtered_df['Date'].between(trade_date, trade_date + timedelta(days=date_window)))]

        matches = len(matching_rates)
        # 거래 성사 df 생성
        for _, rate_row in matching_rates.iterrows():
            matched_rates.append({
                'currency': currency,
                'order_type': '매수' if is_buy_order else '매도',
                'trade_price': trade_price,
                'highPrice': rate_row['high'],
                'LowPrice': rate_row['low'],
                'basePrice': rate_row['close'],
                'trade_executedAt': trade_date,
                'createdAt': rate_row['Date'],
            })
        # 결과 df 생성
        results.append({
            'currency': currency,
            'order_type': '매수' if is_buy_order else '매도',
            'original_price': trade_price,
            'target_price': target_price,
            'found': matches > 0,
            'match_count': matches,
            'executedAt': trade_date,
        })

    return pd.DataFrame(results), pd.DataFrame(matched_rates)

# Sidebar 설정
st.sidebar.header('설정')
# 날짜 설정
max_date = max(final_df['Date'].max(), trade_df['executedAt'].max())
one_week_ago = max_date - timedelta(days=7)

start_date = pd.Timestamp(st.sidebar.date_input('시작일', one_week_ago))
end_date = pd.Timestamp(st.sidebar.date_input('종료일', max_date))

# 목표가 설정
buy_price_adjustment = st.sidebar.slider('매수 목표가 조정값', 0.0, 10.0, 1.0, 0.5)
sell_price_adjustment = st.sidebar.slider('매도 목표가 조정값', 0.0, 10.0, 1.0, 0.5)

# 분석 기간 설정
date_window = st.sidebar.slider('환율 분석 기간(일)', 1, 30, 5)

# 통화 설정
available_currencies = ['USD', 'JPY', 'CAD']
selected_currencies = st.sidebar.multiselect('통화 선택', available_currencies, default=available_currencies)

# 데이터 필터링
filtered_trade_df = trade_df[(trade_df.apply(lambda x: (x['currencyCode0'] if x['currencyCode'] == 'KRW' else x['currencyCode']) in selected_currencies, axis=1)) &
                             (trade_df['executedAt'].between(start_date, end_date))]

# final_df의 시간 부분을 23:59:59로 설정
final_df['Date'] = pd.to_datetime(final_df['Date']).dt.floor('D') + pd.Timedelta(hours=15, minutes=59, seconds=59)

filtered_df = final_df[(final_df['currencyCode'].isin(selected_currencies)) &
                       (final_df['Date'] >= start_date)]

# 분석 실행
results_df, matched_rates_df = analyze_target_prices(filtered_df, filtered_trade_df, buy_price_adjustment, sell_price_adjustment, date_window)

# 결과 표시
st.title('환율 목표가 분석 (야후 파이낸스)')
st.header('분석 결과')

col1, col2, col3 = st.columns(3)
col1.metric('전체 거래 수', len(results_df))
col2.metric('목표가 도달 거래 수', results_df['found'].sum())
col3.metric('목표가 도달률', f"{(results_df['found'].mean() * 100):.2f}%")

currency_analysis = results_df.groupby(['currency', 'order_type']).agg({'found': ['count', 'sum'], 'match_count': 'sum'}).reset_index()
currency_analysis.columns = ['currency', 'order_type', '전체 거래', '목표가 도달', '총 매칭 횟수']
# 거래 성사률 계산 (목표가 도달 / 전체 거래) * 100
currency_analysis['거래 성사률 (%)'] = ((currency_analysis['목표가 도달'] / currency_analysis['전체 거래']) * 100).round(2)

st.subheader('통화별 목표가 도달 거래 수')
st.dataframe(currency_analysis)

st.subheader('매수 및 매도 목표가 도달 거래 수 바 차트')
fig_bar = px.bar(currency_analysis, x='currency', y='목표가 도달', color='order_type',
                 title='통화별 매수 및 매도 목표가 도달 거래 수',
                 labels={'목표가 도달': '목표가 도달 거래 수', 'currency': '통화'})
st.plotly_chart(fig_bar)

if not matched_rates_df.empty:
    st.subheader('목표가 도달 데이터')
    matched_rates_df['time_diff'] = matched_rates_df['trade_executedAt'] - matched_rates_df['createdAt']
    st.dataframe(matched_rates_df)
    AgGrid(matched_rates_df, editable=True, filter=True, sortable=True, resizable=True)
else:
    st.warning('선택한 기간 동안 목표가에 도달한 데이터가 없습니다.')

# 목표가 도달 못한 거래 데이터 필터링
not_matched_df = results_df[results_df['found'] == False]

# 목표가 도달 못한 거래 데이터 표시
st.subheader('목표가 도달 못한 거래 데이터')
if not not_matched_df.empty:
    st.dataframe(not_matched_df)
else:
    st.warning('목표가 도달 못한 거래 데이터가 없습니다.')



# 고가-저가 차이 시각화 함수
def plot_high_low_difference(df, currency, title_suffix=''):
    currency_df = df[df['currencyCode'] == currency]
    currency_df['high_low_diff'] = currency_df['high'] - currency_df['low']
    return px.line(currency_df, x='Date', y='high_low_diff',
                   title=f'{currency} 하루 고가와 저가 차이 {title_suffix}',
                   labels={'high_low_diff': '고가 - 저가 차이', 'Date': '날짜'})

# 고가-저가 차이 시각화
st.subheader('하루 고가와 저가 차이 시계열 (전체)')
for currency in selected_currencies:
    st.plotly_chart(plot_high_low_difference(final_df, currency))

st.subheader('하루 고가와 저가 차이 시계열 (날짜 필터링)')
filtered_df = final_df[final_df['Date'].between(start_date, end_date)]
for currency in selected_currencies:
    st.plotly_chart(plot_high_low_difference(filtered_df, currency, title_suffix='(필터링)'))

# 환율 시계열 (고가, 저가, 종가) 함수
def plot_currency(df, currency):
    currency_df = df[df['currencyCode'] == currency]
    return px.line(currency_df, x='Date', y=['high', 'low', 'close'],
                   title=f'{currency} 환율 시계열 (고가, 저가, 종가)',
                   labels={'value': '환율', 'Date': '날짜'}, line_shape='linear')

# 통화별 시계열 차트
for currency in selected_currencies:
    st.plotly_chart(plot_currency(filtered_df, currency))

# 고가-시가, 시가-저가 변동 시각화
st.subheader('고가-시가 및 시가-저가 변동 시각화')
filtered_currency_df = final_df[final_df['currencyCode'].isin(selected_currencies)]
filtered_currency_df['high_to_open'] = filtered_currency_df['high'] - filtered_currency_df['open']
filtered_currency_df['open_to_low'] = filtered_currency_df['open'] - filtered_currency_df['low']

for currency in selected_currencies:
    currency_df = filtered_currency_df[filtered_currency_df['currencyCode'] == currency]
    st.markdown(f"**{currency} 평균:** 고가-시가: {currency_df['high_to_open'].mean():.2f}, 시가-저가: {currency_df['open_to_low'].mean():.2f}")
    fig = px.line(currency_df, x='Date', y=['high_to_open', 'open_to_low'],
                  title=f'{currency} 환율 변동 폭 (고가-시가, 시가-저가)',
                  labels={'value': '변동 폭', 'Date': '날짜'}, line_shape='linear')
    st.plotly_chart(fig)
