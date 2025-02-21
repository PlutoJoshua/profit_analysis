import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import plotly.express as px
from data import load_data
import itertools
            # matching_rates = filtered_df[
            #     (filtered_df['currencyCode'] == currency) & 
            #     (filtered_df['basePrice'] <= target_price)  
            # ]

def analyze_target_prices(filtered_df, trade_df, start_date, end_date, buy_price_adjustment, sell_price_adjustment, date_window):
    # 날짜 필터링
    filtered_df = filtered_df[(filtered_df['createdAt'] >= start_date) & 
                             (filtered_df['createdAt'] <= end_date)]
    trade_df = trade_df[(trade_df['executedAt'] >= start_date) & 
                        (trade_df['executedAt'] <= end_date)]
    
    results = []
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
# min_date = min(final_df['createdAt'].min(), trade_df['executedAt'].min())
max_date = max(final_df['createdAt'].max(), trade_df['executedAt'].max())
# 가장 최근 날짜 기준 일주일 전 계산
one_week_ago = max_date - timedelta(days=7)

start_date = st.sidebar.date_input('시작일', one_week_ago)
end_date = st.sidebar.date_input('종료일', max_date)

# 분석 기간 설정
date_window = st.sidebar.slider('환율 분석 기간(일)', 1, 30, 1)

# 목표가 조정값 선택
buy_price_adjustment = st.sidebar.slider('매수 목표가 조정값', 0.0, 10.0, 1.0, 0.5)
sell_price_adjustment = st.sidebar.slider('매도 목표가 조정값', 0.0, 10.0, 1.0, 0.5)

# 통화 선택
available_currencies = ['USD', 'JPY']
selected_currencies = st.sidebar.multiselect('통화 선택', available_currencies, default=available_currencies)

# 확인 버튼 추가
if st.sidebar.button('분석 실행'):

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

    results_df, matched_rates_df = analyze_target_prices(filtered_df, filtered_trade_df, start_datetime, end_datetime, buy_price_adjustment, sell_price_adjustment, date_window)

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
    currency_analysis['거래 성사률 (%)'] = ((currency_analysis['목표가 도달'] / currency_analysis['전체 거래']) * 100).round(2)
    st.dataframe(currency_analysis)

    st.markdown("---")
    # 통화별 분석 결과 표시
    st.subheader('통화별 목표가 도달 거래 수')
    currency_analysis = results_df.groupby(['currency', 'order_type']).agg({
        'found': ['count', 'sum'],
        'match_count': 'sum'
    }).round(2)
    currency_analysis.columns = ['전체 거래', '목표가 도달', '총 매칭 횟수']
    currency_analysis = currency_analysis.reset_index()
    st.dataframe(currency_analysis)

    st.markdown("---")
    # 매수와 매도에 대한 바 차트 시각화
    st.subheader('매수 및 매도 목표가 도달 거래 수 바 차트')
    fig_bar = px.bar(currency_analysis, 
                    x='currency', 
                    y='목표가 도달', 
                    color='order_type', 
                    title='통화별 매수 및 매도 목표가 도달 거래 수',
                    labels={'목표가 도달': '목표가 도달 거래 수', 'currency': '통화'})
    st.plotly_chart(fig_bar)

    # 거래 데이터 표시
    st.subheader('거래 데이터')
    st.dataframe(filtered_trade_df)

    # 목표가 도달 데이터 표시
    if not matched_rates_df.empty:
        st.subheader('목표가 도달 데이터')
        matched_rates_df['time_diff'] = matched_rates_df['createdAt'] - matched_rates_df['trade_executedAt']
        # 시간순으로 정렬
        matched_rates_df = matched_rates_df.sort_values(['currency', 'createdAt'])
        st.dataframe(matched_rates_df)
    else:
        st.warning('선택한 기간 동안 목표가에 도달한 데이터가 없습니다.')

    # 목표가 도달 못한 거래 데이터 필터링
    not_matched_df = results_df[results_df['found'] == False]

    # 목표가 도달 못한 거래 데이터 표시
    st.subheader('⚡️ 목표가 도달 못한 거래 데이터')
    if not not_matched_df.empty:
        st.dataframe(not_matched_df)
    else:
        st.warning('목표가 도달 못한 거래 데이터가 없습니다.')

    # # 환율 데이터 표시
    # st.subheader('전체 환율 데이터')
    # st.dataframe(filtered_df)

    # Streamlit 세션 상태 초기화
    if 'cached_analysis' not in st.session_state:
        st.session_state.cached_analysis = pd.DataFrame(columns=['currency', 'order_type', '전체 거래', '목표가 도달', '총 매칭 횟수', '거래 성사률 (%)', '분석 설명'])

    # 누적된 결과 초기화 버튼
    if st.button('누적된 결과 초기화'):
        st.session_state.cached_analysis = pd.DataFrame(columns=['currency', 'order_type', '전체 거래', '목표가 도달', '총 매칭 횟수', '거래 성사률 (%)', '분석 설명'])
        st.success("누적된 결과가 초기화되었습니다.")
        # 페이지 리로드로 상태 초기화 반영
        st.experimental_rerun()
    # 새 분석 결과 생성
    currency_analysis = results_df.groupby(['currency', 'order_type']).agg({
        'found': ['count', 'sum'],
        'match_count': 'sum'
    }).round(2)
    currency_analysis.columns = ['전체 거래', '목표가 도달', '총 매칭 횟수']
    currency_analysis['거래 성사률 (%)'] = ((currency_analysis['목표가 도달'] / currency_analysis['전체 거래']) * 100).round(2)
    currency_analysis = currency_analysis.reset_index()
    # 현재 분석에 대한 설명 생성
    analysis_description = f"date_window={date_window}, 매수 목표가={buy_price_adjustment}, 매도 목표가={sell_price_adjustment}"

    # 설명 컬럼 추가
    currency_analysis['분석 설명'] = analysis_description


    if not currency_analysis.empty:
        # 기존 데이터와 새 데이터 누적 저장
        st.session_state.cached_analysis = pd.concat([st.session_state.cached_analysis, currency_analysis], ignore_index=True).drop_duplicates().reset_index(drop=True)

    # 누적된 결과 출력
    st.subheader('누적된 통화별 목표가 도달 거래 수')
    st.dataframe(st.session_state.cached_analysis, use_container_width=True)

# 버튼 클릭 시 여러 시뮬레이션 실행
if st.sidebar.button('모든 조합 시뮬레이션 실행'):
    # 가능한 모든 조합 생성
    date_windows = range(1, 8)  # 1일부터 7일까지
    buy_adjustments = [i * 1.0 for i in range(1, 6)]  # 매수 목표가: 1.0 ~ 5.0
    sell_adjustments = [i * 1.0 for i in range(1, 6)]  # 매도 목표가: 1.0 ~ 5.0

    # 모든 조합 생성
    all_combinations = itertools.product(date_windows, buy_adjustments, sell_adjustments)

    # 결과 저장용 리스트
    simulation_results = []

    # 각 조합에 대해 분석 실행
    for date_window, buy_adjustment, sell_adjustment in all_combinations:
        # 분석 실행
        results_df, _ = analyze_target_prices(
            filtered_df, 
            filtered_trade_df, 
            start_datetime, 
            end_datetime, 
            buy_adjustment, 
            sell_adjustment, 
            date_window
        )

        # 현재 조합에 대한 설명
        analysis_description = f"date_window={date_window}, 매수 목표가={buy_adjustment}, 매도 목표가={sell_adjustment}"

        # 통화별 분석
        currency_analysis = results_df.groupby(['currency', 'order_type']).agg({
            'found': ['count', 'sum'],
            'match_count': 'sum'
        }).round(2)
        currency_analysis.columns = ['전체 거래', '목표가 도달', '총 매칭 횟수']
        currency_analysis['거래 성사률 (%)'] = ((currency_analysis['목표가 도달'] / currency_analysis['전체 거래']) * 100).round(2)
        currency_analysis = currency_analysis.reset_index()

        # 설명 추가
        currency_analysis['분석 설명'] = analysis_description

        # 결과 누적
        simulation_results.append(currency_analysis)

    # 모든 결과를 하나의 DataFrame으로 병합
    all_simulations_df = pd.concat(simulation_results, ignore_index=True)

    # 기존 누적된 데이터에 병합
    st.session_state.cached_analysis = pd.concat(
        [st.session_state.cached_analysis, all_simulations_df],
        ignore_index=True
    ).drop_duplicates().reset_index(drop=True)

    st.success("모든 조합 시뮬레이션이 완료되었습니다.")

# 누적된 결과 출력
st.subheader('누적된 통화별 목표가 도달 거래 수')
st.dataframe(st.session_state.cached_analysis, use_container_width=True)