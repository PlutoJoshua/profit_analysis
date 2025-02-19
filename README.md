# profit_analysis
profit_analysis

이 코드는 환율 목표가 분석을 위한 Streamlit 웹 애플리케이션을 만드는 데 사용됩니다. 이 앱을 통해 사용자는 거래 데이터를 기반으로 목표가에 도달한 거래를 분석하고 시각화할 수 있습니다.

# 1. 프로젝트 소개
프로젝트 제목: 환율 목표가 분석 (야후 파이낸스)
목표: 다양한 통화의 매수 및 매도 목표가 도달 여부를 분석하고, 이를 기반으로 투자 전략을 수립할 수 있도록 도와주는 분석 도구 제공.
사용 기술: Python, Pandas, Plotly, Streamlit, Yahoo Finance API, 데이터 전처리 및 시각화
문제 해결: 특정 목표가에 도달한 거래를 식별하고 이를 통계적으로 분석, 사용자 맞춤형 설정을 통해 분석할 수 있는 기능 제공

# 2. 기능 설명
시작일, 종료일 선택: 사용자가 분석할 기간을 선택
목표가 조정값 설정: 매수 및 매도 목표가에 대한 사용자 조정값 설정
통화 선택: 분석할 통화를 사용자가 선택할 수 있음 (USD, JPY, CNY, CAD 등)
분석: 거래 데이터와 환율 데이터에서 목표가에 도달한 거래를 매칭하고, 결과를 시각화
결과 시각화:
전체 거래 수, 목표가 도달 거래 수, 목표가 도달률을 한눈에 확인
매수와 매도별로 목표가 도달 거래 수를 바 차트로 시각화
목표가에 도달한 데이터의 상세 목록을 테이블 형식으로 표시

# 3. 분석 프로세스
데이터 로드 및 전처리:
거래 데이터와 야후 파이낸스에서 제공하는 환율 데이터를 로드.
사용자가 선택한 기간과 통화에 맞는 데이터 필터링.
목표가 도달 여부 분석:
매수와 매도 거래에 대해 목표가를 설정하고, 해당 목표가가 고가 또는 저가 범위에 포함되는지 체크.
목표가에 도달한 거래들을 추출하여 분석 결과에 포함.
결과 계산:
전체 거래 수, 목표가에 도달한 거래 수, 목표가 도달률 계산.
매수와 매도에 대한 분석 결과를 계산하여 시각화.

# 4. 시각화 및 대시보드
전체 거래 분석: 전체 거래 수, 목표가 도달 거래 수, 목표가 도달률을 각각 Streamlit의 metric 위젯을 사용해 간단히 표시.
통화별 분석: 각 통화별로 목표가 도달 거래 수와 매칭 횟수를 분석하여 dataframe으로 표시.
바 차트 시각화: Plotly를 사용하여 매수와 매도별 목표가 도달 거래 수를 시각화한 바 차트 제공.
목표가 도달한 거래 데이터: 목표가에 도달한 거래의 상세 데이터를 정렬하여 테이블 형식으로 표시.