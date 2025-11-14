import pandas as pd
import matplotlib.pyplot as plt
import os

# --- 1. 설정 ---
# (데이터 수집에 사용한 파일명과 동일해야 함)
FILENAME = 'digital_twin_data_no_mfc40.csv'

# --- 2. 데이터 로드 ---
if not os.path.isfile(FILENAME):
    print(f"[오류] 파일 '{FILENAME}'을 찾을 수 없습니다.")
else:
    print(f"데이터 파일 '{FILENAME}'을 로드합니다...")
    df = pd.read_csv(FILENAME)

    # --- 3. 데이터 시각화 ---

    print("데이터 시각화를 생성합니다...")

    fig, ax1 = plt.subplots(figsize=(12, 7))

    # 1축 (왼쪽 Y축): 온도 (Actual Temp (C))
    color = 'tab:red'
    ax1.set_xlabel('Elapsed Time (s)')
    ax1.set_ylabel('Actual Temp (°C)', color=color)
    ax1.plot(df['Elapsed Time (s)'], df['Actual Temp (C)'], color=color, label='Actual Temp')
    ax1.tick_params(axis='y', labelcolor=color)

    # 2축 (오른쪽 Y축): 히터 출력 (Target Output (%))
    ax2 = ax1.twinx()
    color = 'tab:blue'
    ax2.set_ylabel('Target Output (%)', color=color)
    # (출력 그래프가 계단식으로 보이도록 'drawstyle'을 'steps-post'로 설정)
    ax2.plot(df['Elapsed Time (s)'], df['Target Output (%)'], color=color, label='Heater Output',
             drawstyle='steps-post', linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color)

    # 그래프 설정
    fig.suptitle('Heater Step Response Data (System ID)', fontsize=16)
    fig.tight_layout()  # 레이아웃 최적화
    plt.legend([ax1.get_lines()[0], ax2.get_lines()[0]], ['Actual Temp', 'Heater Output'])
    plt.grid(True)

    # 그래프 저장 및 표시
    plt.savefig('step_response_40.png')
    print("그래프가 'step_response_40.png' 파일로 저장되었습니다.")

    plt.show()