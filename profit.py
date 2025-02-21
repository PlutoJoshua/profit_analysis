import pandas as pd
from datetime import datetime, timedelta


def analyze_target_prices(filtered_df, trade_df, start_date, end_date, buy_price_adjustment, sell_price_adjustment, date_window):
    # 날짜 필터링
    filtered_df = filtered_df[(filtered_df['createdAt'] >= start_date) & 
                             (filtered_df['createdAt'] <= end_date + timedelta(days=date_window))]
    trade_df = trade_df[(trade_df['executedAt'] >= start_date) & 
                        (trade_df['executedAt'] <= end_date + timedelta(days=date_window))]
    
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

# 수익 계산 함수
def calculate_profit(results_df, adjustment, start_date, end_date):
    # start_date와 end_date를 datetime64[ns]로 변환
    start_datetime = pd.to_datetime(start_date)
    end_datetime = pd.to_datetime(end_date)
    
    # 'found'가 True인 경우에만 수익 계산
    profit_df = results_df[
        (results_df['executedAt'] >= start_datetime) &
        (results_df['executedAt'] <= end_datetime) &
        (results_df['found'] == True)
    ]
    
    # 수익 계산 (총 거래량 * 매수/매도 조정값)
    profit_df['profit'] = profit_df['amount'] * adjustment
    total_amo = profit_df['amount'].sum()
    total_pro = profit_df['profit'].sum()
    return profit_df, total_amo, total_pro