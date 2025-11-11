# 파일 이름: collect_digital_twin_data.py
import minimalmodbus
import serial  # (minimalmodbus의 파라미터 설정을 위해 필요)
import time
import csv
import os
import numpy as np
from datetime import datetime

# [수정된 권장 주소] - VX Series 매뉴얼 기반
VX_PORT = 'COM3'
VX_SLAVE_ID = 1
PV_ADDRESS = 0            # D-Reg 0: 현재 온도(PV)
R_S_ADDR = 33             # D-Reg 33: Run/Stop (0=STOP, 1=RUN)
A_M_ADDR = 31             # D-Reg 31: Auto/Manual (0=AUTO, 1=MANU)
MV_IN_ADDR = 32           # D-Reg 32: 수동 출력량 입력 (0.0 ~ 100.0)

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

def set_run_stop(vx, is_run):
    """VX를 RUN 또는 STOP 모드로 설정합니다. (D-Reg 33)"""
    try:
        mode_value = 1 if is_run else 0
        # D-Reg 33 (R/S)에 0 또는 1 쓰기 (FC 06 또는 16)
        vx.write_register(R_S_ADDR, mode_value, 0, 16)
        status = "RUN" if is_run else "STOP"
        print(f"VX: {status} 모드 설정 (주소 {R_S_ADDR}에 값 {mode_value} 전송)")
    except Exception as e:
        print(f"VX: RUN/STOP 모드 변경 실패: {e}")

def set_auto_manual(vx, is_manual):
    """VX를 AUTO 또는 MANUAL 모드로 설정합니다. (D-Reg 31)"""
    try:
        mode_value = 1 if is_manual else 0
         # D-Reg 31 (A/M)에 0 또는 1 쓰기 (FC 06 또는 16)
        vx.write_register(A_M_ADDR, mode_value, 0, 16)
        status = "MANUAL" if is_manual else "AUTO"
        print(f"VX: {status} 모드 설정 (주소 {A_M_ADDR}에 값 {mode_value} 전송)")
    except Exception as e:
        print(f"VX: AUTO/MANUAL 모드 변경 실패: {e}")

def set_vx_manual_output(vx, output_percent):
    """VX 수동 출력값을 설정합니다. (D-Reg 32) (소수점 1자리)"""
    try:
        # 매뉴얼(8551)에 MV IN은 소수점 1자리를 사용합니다.
        safe_output = max(0.0, min(100.0, output_percent))
        # minimalmodbus는 소수점 자릿수(1)를 인자로 전달해야 합니다.
        vx.write_register(MV_IN_ADDR, safe_output, 1, 16)
        print(f"VX: 수동 출력 설정 (주소 {MV_IN_ADDR}에 값 {safe_output} 전송)")
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

        # 1. 테스트 준비: (매뉴얼 기반) 순차적 모드 변경
        # (주의: 2단계에서 DI.MD=OFF, LOCK=0이 선행되어야 함)

        print("VX: 1단계 - RUN 모드 진입")
        set_run_stop(v, True)  # (D-Reg 33 = 1)
        time.sleep(0.5)

        print("VX: 2단계 - MANUAL 모드 진입")
        set_auto_manual(v, True)  # (D-Reg 31 = 1)
        time.sleep(0.5)

        print("VX: 3단계 - 수동 출력 0% 설정")
        set_vx_manual_output(v, 0.0)  # (D-Reg 32 = 0.0)

        print("초기 안정화 대기 중 (30초)...")
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

            set_vx_manual_output(v, 0.0)  # 히터 출력 0% (D-Reg 32)

            set_auto_manual(v, False)  # AUTO 모드 복귀 (D-Reg 31)

            set_run_stop(v, True)  # RUN 상태 유지 (D-Reg 33)

            v.serial.close()

            print("VX 컨트롤러 (RUN + AUTO) 모드 복귀 및 연결 해제됨.")