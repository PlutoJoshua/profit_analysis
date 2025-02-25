import streamlit as st
import pandas as pd
import json
from datetime import datetime
import plotly.express as px

# 데이터 로드 함수
@st.cache_data # 함수가 실행되고 결과 캐시 저장
def load_data():
    # 매매기준율 데이터 로드 및 전처리 코드
    df = pd.read_csv('../mama.csv', sep='\t', dtype=str)
    df.columns = ['createdAt,data']
    df = df['createdAt,data'].str.split(',', n=1, expand=True)
    df.columns = ['createdAt', 'data']
    
    # JSON 파싱 함수
    def parse_json(json_str, created_at=None):
        try:
            # 앞부분 따옴표 제거
            json_str = json_str.replace('"{"result":', '{"result":')
            # 뒷부분 따옴표 제거
            if json_str.endswith('}]}"'): # '}]}"'로 끝나는지 확인
                json_str = json_str[:-1]
            data = json.loads(json_str)
            result_df = pd.DataFrame(data['result'])
            # 시간 추가
            if created_at is not None:
                result_df['createdAt'] = created_at
            return result_df
        except Exception as e:
            return None

    # 전체 데이터 처리
    parsed_data = []
    for _, row in df.iterrows(): # 각 행 순회
        result = parse_json(row['data'], row['createdAt'])
        if result is not None:
            result['createdAt'] = pd.to_datetime(result['createdAt'], format='%Y-%m-%d %H:%M:%S') + pd.Timedelta(hours=9) # UTC -> KST
            parsed_data.append(result)
    
    final_df = pd.concat(parsed_data, ignore_index=True)
    
    # 거래 데이터 로드
    trade_df = pd.read_csv('../trade.csv')
    trade_df['executedAt'] = pd.to_datetime(trade_df['executedAt'], format='%Y-%m-%d %H:%M:%S') + pd.Timedelta(hours=9) # UTC -> KST
    
    return final_df, trade_df

# 데이터 로드 함수
@st.cache_data # 함수가 실행되고 결과 캐시 저장
def load_trade_data():
    # 거래 데이터 로드
    trade_df = pd.read_csv('./trade_08_02.csv')
    trade_df['executedAt'] = pd.to_datetime(trade_df['executedAt'], format='%Y-%m-%d %H:%M:%S') + pd.Timedelta(hours=9) # UTC -> KST
    
    return trade_df

# 데이터 로드 함수
@st.cache_data # 함수가 실행되고 결과 캐시 저장
def load_final_data():
    # 데이터 로드
    final_df = pd.read_csv('./final.csv')
    final_df['createdAt'] = pd.to_datetime(final_df['createdAt'], format='%Y-%m-%d %H:%M:%S') + pd.Timedelta(hours=9) # UTC -> KST
    
    return final_df
def load_yh_data():
    # 야후 데이터 로드 
    final_df = pd.read_csv('../yh.csv')
    final_df['Date'] = pd.to_datetime(final_df['Date'], format='%Y-%m-%d') + pd.Timedelta(hours=9) # UTC -> KST

    return final_df


def filter_trade_data(trade_df, selected_currencies):
    """주어진 통화에 따라 거래 데이터를 필터링하는 함수"""
    return trade_df[
        trade_df.apply(lambda x: 
            (x['currencyCode0'] if x['currencyCode'] == 'KRW' else x['currencyCode']) in selected_currencies, 
            axis=1
        )
    ]