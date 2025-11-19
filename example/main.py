import pandas as pd
import matplotlib.pyplot as plt
import os

# --- 1. 설정 ---
DATA_DIR = '../data/step_response'
RESULT_DIR = '../example_results/step_response'

# 결과 저장 폴더가 없으면 생성 (에러 방지)
os.makedirs(RESULT_DIR, exist_ok=True)

# DATA_DIR이 존재하는지 확인
if not os.path.exists(DATA_DIR):
    print(f"[오류] 데이터 폴더 '{DATA_DIR}'을 찾을 수 없습니다.")
    exit()

for FILE in os.listdir(DATA_DIR):
    # .csv 파일만 처리하도록 필터링 (선택 사항)
    if not FILE.endswith('.csv'):
        continue

    FILENAME = os.path.join(DATA_DIR, FILE)

    # --- 2. 데이터 로드 ---
    print(f"데이터 파일 '{FILENAME}'을 로드합니다...")
    try:
        df = pd.read_csv(FILENAME)
    except Exception as e:
        print(f"[오류] 파일을 읽는 중 문제가 발생했습니다: {e}")
        continue

    # --- 3. 데이터 시각화 ---
    print("데이터 시각화를 생성합니다...")

    fig, ax1 = plt.subplots(figsize=(12, 7))

    # 1축 (왼쪽 Y축): 온도
    color_temp = 'tab:red'
    ax1.set_xlabel('Elapsed Time (s)')
    ax1.set_ylabel('Actual Temp (°C)', color=color_temp)
    line1 = ax1.plot(df['Elapsed Time (s)'], df['Actual Temp (C)'],
                     color=color_temp, label='Actual Temp')
    ax1.tick_params(axis='y', labelcolor=color_temp)

    # 2축 (오른쪽 Y축): 히터 출력 (Target & Actual)
    ax2 = ax1.twinx()
    color_output = 'tab:blue'
    ax2.set_ylabel('Output (%)', color=color_output)

    # [수정] 각 열을 개별적으로 plot하여 스타일 구분 및 문법 오류 해결
    # Target Output: 점선 등으로 구별
    line2 = ax2.plot(df['Elapsed Time (s)'], df['Target Output (%)'],
                     color='black', linestyle='--', alpha=0.5, drawstyle='steps-post', label='Target Output')
    # Actual Output: 실선
    line3 = ax2.plot(df['Elapsed Time (s)'], df['Actual Output (%)'],
                     color=color_output, linestyle='-', drawstyle='steps-post', label='Actual Output')

    ax2.tick_params(axis='y', labelcolor=color_output)

    # 그래프 설정
    fig.suptitle(f'Heater Step Response: {FILE}', fontsize=16)
    fig.tight_layout()

    # [수정] 범례 통합 (ax1과 ax2의 라인을 합쳐서 표시)
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper right')

    plt.grid(True)

    # [수정] 파일명에서 .csv 제거 후 .png로 저장
    save_name = os.path.splitext(FILE)[0] + '.png'
    save_path = os.path.join(RESULT_DIR, save_name)

    plt.savefig(save_path)
    print(f"그래프가 '{save_path}'로 저장되었습니다.\n")

    # 주의: plt.show()는 루프를 멈추게 하므로, 연속 처리를 원하면 주석 처리하세요.
    # plt.show()
    plt.close(fig)  # 메모리 누수 방지를 위해 Figure 닫기