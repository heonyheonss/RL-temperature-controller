# 파일 이름: collect_digital_twin_data.py
import minimalmodbus
import serial  # (minimalmodbus의 파라미터 설정을 위해 필요)
import time
import csv
import os
import numpy as np
from datetime import datetime

# --- [1. Modbus 주소 (커스텀 PID/RL용)] ---
VX_PORT = 'COM3'
VX_SLAVE_ID = 1
PV_ADDRESS = 0            # VX: 현재 온도(PV) 읽기 주소
MANUAL_MODE_ADDR = 20     # [수정] D-Register 19가 아닌, Modbus 주소 20
MANUAL_VALUE_ADDR = 33    # [수정] D-Register 32가 아닌, Modbus 주소 33

# --- [2. 데이터 로깅 설정] ---
FILENAME = 'digital_twin_data_no_mfc100.csv'
FIELDNAMES = [
    'Timestamp',
    'Elapsed Time (s)',
    'Target Output (%)',  # (Python이 설정한 히터 출력)
    'Actual Temp (C)'
]


# --- [3. VX 제어 함수] ---
def connect_vx(port, slave_id):
    """HANYOUNG NUX VX에 연결하고 객체를 반환합니다."""
    print(f"Connecting to HANYOUNG VX ({port})...")
    try:
        instrument = minimalmodbus.Instrument(port, slave_id, mode='rtu')
        instrument.serial.baudrate = 9600
        instrument.serial.bytesize = 8
        instrument.serial.parity = serial.PARITY_NONE  # (serial 라이브러리 필요)
        instrument.serial.stopbits = 1
        instrument.serial.timeout = 0.5  # (샘플 타임보다 짧아야 함)
        print("HANYOUNG VX Connected.")
        return instrument
    except Exception as e:
        print(f"VX 연결 실패: {e}")
        return None


def read_temperature(vx):
    try:
        temp = vx.read_register(PV_ADDRESS, 1, 3)
        return temp
    except Exception as e:
        print(f"VX: 온도 읽기 실패: {e}")
        return None


def set_vx_manual_mode(vx, mode_value):
    """[수정] VX에 Modbus 주소 20번으로 제어 값을 전송합니다."""
    try:
        # 주소 20(DEC)에 값(0, 1, 9, 13 등)을 씁니다. (소수점 0자리, FC16)
        vx.write_register(MANUAL_MODE_ADDR, mode_value, 0, 16)

        # [수정] 버그를 잡고 실제 전송된 값을 출력
        print(f"VX: 제어 모드 설정 시도 (주소 {MANUAL_MODE_ADDR}에 값 {mode_value} 전송)")

    except Exception as e:
        print(f"VX: 제어 모드 변경 실패: {e}")

def set_vx_manual_output(vx, output_percent):
    try:
        safe_output = max(0.0, min(100.0, output_percent))
        vx.write_register(MANUAL_VALUE_ADDR, safe_output, 1, 16)
    except Exception as e:
        print(f"VX: 수동 출력 설정 실패: {e}")


def log_dt_data(filename, fieldnames, data_dict):
    """Digital Twin 데이터를 CSV에 저장합니다."""
    file_exists = os.path.isfile(filename)
    try:
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists: writer.writeheader()
            writer.writerow(data_dict)
    except Exception as e:
        print(f"Data Logging: [오류] 파일 저장 실패: {e}")


# --- [4. 메인 실행 블록 (Step Response 테스트)] ---
if __name__ == "__main__":

    # --- 테스트 파라미터 [사용자 설정 필요] ---
    STEP_OUTPUT = 100.0  # (입력) 100% 히터 출력
    SAMPLE_TIME_S = 1.0  # (수집) 1.0초 간격
    HEAT_DURATION_S = 300  # (시간) 300초 (5분) 가열
    COOL_DURATION_S = 300  # (시간) 300초 (5분) 냉각

    v = None
    print(f"--- Digital Twin 데이터 수집 (MFC 없음) 시작 ---")
    print(f"가열: {STEP_OUTPUT}% ( {HEAT_DURATION_S}초간 )")
    print(f"냉각: 0.0% ( {COOL_DURATION_S}초간 )")

    try:
        v = connect_vx(VX_PORT, VX_SLAVE_ID)
        if v is None:
            raise ConnectionError("VX 컨트롤러 연결 실패. 스크립트를 종료합니다.")

        # 1. 테스트 준비: [최종 수정] 3단계 순차적 모드 변경

        # 1-A. (STOP + AUTO) 상태에서 (RUN + AUTO) 상태로 변경 (값 1)
        print("VX: 1단계 - RUN 모드 진입 (Bit 0 = 1)")
        set_vx_manual_mode(v, 1)  # 1 = (Bit 0: RUN)
        time.sleep(0.5)

        # 1-B. (RUN + AUTO) 상태에서 (RUN + AUTO + REM) 상태로 변경 (값 9)
        print("VX: 2단계 - REM 모드 진입 (Bit 0 = 1, Bit 3 = 8)")
        set_vx_manual_mode(v, 9)  # 9 = 1(RUN) + 8(REM)
        time.sleep(0.5)

        # 1-C. (RUN + AUTO + REM) 상태에서 (RUN + MANUAL + REM) 상태로 변경 (값 13)
        print("VX: 3단계 - MANUAL 모드 진입 (Bit 0 = 1, Bit 2 = 4, Bit 3 = 8)")
        set_vx_manual_mode(v, 13)  # 13 = 1(RUN) + 4(MANUAL) + 8(REM)

        # 1-D. MANUAL 모드에서 출력 0%로 설정
        set_vx_manual_output(v, 0.0)

        print("초기 안정화 대기 중 (30초)... (챔버 온도를 상온과 같게 하십시오)")
        time.sleep(30)

        start_time = time.time()

        # --- [Phase 1: 가열 (Step-Up)] ---
        set_vx_manual_output(v, STEP_OUTPUT)
        print(f"--- 1단계: 가열 ({STEP_OUTPUT}%) 적용 ---")

        num_heat_steps = int(HEAT_DURATION_S / SAMPLE_TIME_S)

        for i in range(num_heat_steps):
            loop_start_time = time.time()
            current_temp = read_temperature(v)
            if current_temp is None: continue

            elapsed_time = loop_start_time - start_time

            data_to_log = {
                'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Elapsed Time (s)': elapsed_time,
                'Target Output (%)': STEP_OUTPUT,
                'Actual Temp (C)': current_temp
            }
            log_dt_data(FILENAME, FIELDNAMES, data_to_log)
            print(f"가열 중... Time: {elapsed_time:.1f}s / Temp: {current_temp}°C")

            loop_time = time.time() - loop_start_time
            time.sleep(max(0, SAMPLE_TIME_S - loop_time))

        # --- [Phase 2: 자연 냉각 (Step-Down)] ---
        set_vx_manual_output(v, 0.0)  # 히터 끄기
        print(f"--- 2단계: 냉각 (0.0%) 적용 ---")

        num_cool_steps = int(COOL_DURATION_S / SAMPLE_TIME_S)

        for i in range(num_cool_steps):
            loop_start_time = time.time()
            current_temp = read_temperature(v)
            if current_temp is None: continue

            elapsed_time = loop_start_time - start_time

            data_to_log = {
                'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Elapsed Time (s)': elapsed_time,
                'Target Output (%)': 0.0,  # (출력 0%)
                'Actual Temp (C)': current_temp
            }
            log_dt_data(FILENAME, FIELDNAMES, data_to_log)
            print(f"냉각 중... Time: {elapsed_time:.1f}s / Temp: {current_temp}°C")

            loop_time = time.time() - loop_start_time
            time.sleep(max(0, SAMPLE_TIME_S - loop_time))

        print("--- 데이터 수집 완료 ---")



    except Exception as e:

        print(f"\n[메인 오류] 프로세스 중단: {e}")


    finally:

        # 5. 안전 종료

        if v:
            print("VX: 안전 종료 시작...")

            set_vx_manual_output(v, 0.0)  # 히터 출력 0%

            # (RUN + AUTO + REM) 상태로 복귀

            set_vx_manual_mode(v, 9)

            v.serial.close()

            print("VX 컨트롤러 (RUN + AUTO + REM) 모드 복귀 및 연결 해제됨.")