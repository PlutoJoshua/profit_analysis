import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from data import load_data
import itertools
from profit import analyze_target_prices, calculate_profit, display_metrics

# 데이터 로드
final_df, trade_df = load_data()
# Streamlit 앱 메인
st.title('환율 목표가 분석')
tab1, tab2 = st.tabs(['analysis', 'simulation'])

with tab1 : 
    # 사이드바에 필터 추가
    st.sidebar.header('분석 설정')
    # 날짜 범위 선택
    max_date = max(final_df['createdAt'].max(), trade_df['executedAt'].max())
    # 가장 최근 날짜 기준 일주일 전 계산
    one_week_ago = max_date - timedelta(days=7)

    start_date = st.sidebar.date_input('시작일', one_week_ago)
    end_date = st.sidebar.date_input('종료일', max_date)

    # 분석 기간 설정
    date_window = st.slider('환율 분석 기간(일)', 1, 30, 1)
    # 목표가 조정값 선택
    buy_price_adjustment = st.slider('매수 목표가 조정값', 0.0, 10.0, 1.0, 0.5)
    sell_price_adjustment = st.slider('매도 목표가 조정값', 0.0, 10.0, 1.0, 0.5)
    # 통화 선택
    available_currencies = ['USD', 'JPY']
    selected_currencies = st.sidebar.multiselect('통화 선택', available_currencies, default=available_currencies)

    # 확인 버튼 추가
    if st.button('분석 실행'):
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

with tab2 :
    # 사용자 입력 받기
    date_window = st.number_input('환율 분석 기간(일)', min_value=1, max_value=30, value=1)
    adjustment = st.number_input('목표가 조정값', min_value=0, max_value=10, value=1, step=1)
    n_adjustment = st.number_input('현재 조정값', min_value=0, max_value=10, value=1, step=1)
    # 버튼 클릭 시 여러 시뮬레이션 실행
    if st.button('모든 조합 시뮬레이션 실행'):


        # Streamlit 세션 상태 초기화
        if 'cached_analysis' not in st.session_state:
            st.session_state.cached_analysis = pd.DataFrame(columns=['currency', 'order_type', '전체 거래', '목표가 도달', '총 매칭 횟수', '거래 성사률 (%)'])

        # 결과 저장용 리스트
        buy_results = []  # 매수 결과 저장
        sell_results = []  # 매도 결과 저장

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

        n_results_df, matched_rates_df = analyze_target_prices(filtered_df, filtered_trade_df, start_datetime, end_datetime, n_adjustment, n_adjustment, date_window)
        st.success("모든 조합 시뮬레이션이 완료되었습니다.")
        st.dataframe(n_results_df)
        st.markdown(f"---")
        (buy_profit_df, total_buy_amo, total_buy_pro), (sell_profit_df, total_sell_amo, total_sell_pro) = calculate_profit(n_results_df, n_adjustment, start_date, end_date)
        # n_success_rate = (n_results_df['found'].sum() / len(n_results_df)) * 100
         # 전체 통계
        display_metrics(n_results_df, buy_profit_df, sell_profit_df, n_adjustment, total_buy_amo, total_buy_pro, total_sell_amo, total_sell_pro)   
        st.markdown(f"---")        
        n_profit_df = pd.concat([buy_profit_df, sell_profit_df])
        st.dataframe(n_profit_df)

        st.markdown(f"---")
        st.subheader("profit")
        # results_df, matched_rates_df = analyze_target_prices(filtered_df, filtered_trade_df, start_datetime, end_datetime, adjustment, adjustment, date_window)
        # profit_df, total_amo, total_pro = calculate_profit(results_df, adjustment, start_date, end_date)
        # success_rate = (results_df['found'].sum() / len(results_df)) * 100
        # display_metrics(results_df, success_rate, adjustment, total_amo, total_pro)   
        # st.dataframe(profit_df)

        # 가능한 모든 조합 생성
        date_windows = range(1, date_window + 1) 
        adjustments = [i * 1.0 for i in range(1, adjustment + 1)]  # 목표가

        # 모든 조합 생성
        all_combinations = itertools.product(date_windows, adjustments)

        # 각 조합에 대해 분석 실행
        for i, j in all_combinations:
            # 분석 실행
            results_df, _ = analyze_target_prices(
                filtered_df, 
                filtered_trade_df, 
                start_datetime, 
                end_datetime, 
                j, 
                j, 
                i
            )

            # 중복 거래를 제거 (currency, executedAt, amount 기준)
            results_df = results_df.drop_duplicates(subset=['currency', 'executedAt', 'amount'])

            # 통화별 분석
            currency_analysis = results_df.groupby(['currency', 'order_type']).agg({
                'found': ['count', 'sum'],
                'match_count': 'sum',
                'amount': 'sum'  # 거래량 합계 추가
            }).round(2)
            currency_analysis.columns = ['전체 거래', '목표가 도달', '총 매칭 횟수', '총 거래량']

            # 거래 성사률 계산
            currency_analysis['거래 성사률 (%)'] = ((currency_analysis['목표가 도달'] / currency_analysis['전체 거래']) * 100).round(2)
            currency_analysis = currency_analysis.reset_index()

            # 수익 계산 (date_window와 관계없이)
            currency_analysis['profit'] = currency_analysis['총 거래량'] * adjustment

            # 설명 추가
            currency_analysis[['date_window', 'adjustment']] = date_window, adjustment
            # 결과 누적
            if '매수' in currency_analysis['order_type'].values:  # 매수 결과
                buy_results.append(currency_analysis[currency_analysis['order_type'] == '매수'])
            if '매도' in currency_analysis['order_type'].values:  # 매도 결과
                sell_results.append(currency_analysis[currency_analysis['order_type'] == '매도'])

        # 모든 결과를 하나의 DataFrame으로 병합
        all_buy_simulations_df = pd.concat(buy_results, ignore_index=True)
        all_sell_simulations_df = pd.concat(sell_results, ignore_index=True)

        # 기존 누적된 데이터에 병합
        st.session_state.cached_analysis = pd.concat(
            [st.session_state.cached_analysis, all_buy_simulations_df, all_sell_simulations_df],
            ignore_index=True
        ).drop_duplicates().reset_index(drop=True)

        # # 누적된 결과 출력
        # st.subheader('누적된 통화별 목표가 도달 거래 수')
        # st.dataframe(st.session_state.cached_analysis, use_container_width=True)







        # # Streamlit 세션 상태 초기화
    # if 'cached_analysis' not in st.session_state:
    #     st.session_state.cached_analysis = pd.DataFrame(columns=['currency', 'order_type', '전체 거래', '목표가 도달', '총 매칭 횟수', '거래 성사률 (%)'])

    # # 누적된 결과 초기화 버튼
    # if st.button('누적된 결과 초기화'):
    #     st.session_state.cached_analysis = pd.DataFrame(columns=['currency', 'order_type', '전체 거래', '목표가 도달', '총 매칭 횟수', '거래 성사률 (%)'])
    #     st.success("누적된 결과가 초기화되었습니다.")

    # # 새 분석 결과 생성
    # currency_analysis = results_df.groupby(['currency', 'order_type']).agg({
    #     'found': ['count', 'sum'],
    #     'match_count': 'sum',
    #     'amount': 'sum'  # 거래량 합계 추가
    # }).round(2)
    # currency_analysis.columns = ['전체 거래', '목표가 도달', '총 매칭 횟수', '총 거래량']
    # currency_analysis['거래 성사률 (%)'] = ((currency_analysis['목표가 도달'] / currency_analysis['전체 거래']) * 100).round(2)
    # currency_analysis = currency_analysis.reset_index()

    # # 거래량 합계를 date_window 별로 추가
    # currency_analysis['총 거래량'] = results_df.groupby(['currency', 'order_type'])['amount'].sum().reset_index(drop=True)

    # currency_analysis['거래 성사률 (%)'] = ((currency_analysis['목표가 도달'] / currency_analysis['전체 거래']) * 100).round(2)
    # currency_analysis = currency_analysis.reset_index()
    # # profit 계산 추가
    # currency_analysis['profit'] = currency_analysis['총 거래량'] * buy_price_adjustment
    # # 설명 추가
    # currency_analysis[['date_window', 'adjustment']] = date_window, sell_price_adjustment

    # if not currency_analysis.empty:
    #     # 기존 데이터와 새 데이터 누적 저장
    #     st.session_state.cached_analysis = pd.concat([st.session_state.cached_analysis, currency_analysis], ignore_index=True).drop_duplicates().reset_index(drop=True)

    # # 누적된 결과 출력
    # st.subheader('누적된 통화별 목표가 도달 거래 수')
    # st.dataframe(st.session_state.cached_analysis, use_container_width=True)