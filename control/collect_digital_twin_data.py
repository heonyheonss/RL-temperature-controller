# 파일 이름: collect_digital_twin_data.py
import minimalmodbus
import serial  # (minimalmodbus의 파라미터 설정을 위해 필요)
import time
import csv
import os
import numpy as np
from datetime import datetime

from reset_vx_to_safe_state import run_safe_state_reset as rssr

# [수정된 권장 주소] - VX Series 매뉴얼 기반
VX_PORT = 'COM3'
VX_SLAVE_ID = 1

# Process 그룹
PV_ADDRESS = 0            # D-Reg 0: 현재 온도(PV)
MVOUT_ADDRESS = 5         # D-Reg 5 (MVOUT, 출력량)
A_M_ADDR = 31             # D-Reg 31: Auto/Manual (0=AUTO, 1=MANU)
MV_IN_ADDR = 32           # D-Reg 32: 수동 출력량 입력 (0.0 ~ 100.0)
R_S_ADDR = 33             # D-Reg 33: Run/Stop (0=STOP, 1=RUN)

# G.SV 그룹
SV1_ADDR = 103            # [추가] D-Reg 103: SV-1 (설정값 1)


# --- [2. 데이터 로깅 설정] ---
FILENAME_PREFIX = 'step_response_' # 파일명 접두사
FIELDNAMES = [
    'Timestamp',
    'Elapsed Time (s)',
    'Target Output (%)',  # (Python이 설정한 히터 출력)
    'Actual Output (%)', # 컨트롤러가 실제 출력한 내용(OL-H) 반영
    'Actual Temp (C)'
]
SAFE_TEMP = 25.0


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

def read_output_percent(vx):
    """VX의 현재 MVOUT (출력량 %)을 읽습니다. (D-Reg 5, 소수점 1자리)"""
    try:
        # D-Reg 5 (MVOUT), 소수점 1자리, Function Code 3
        mv_percent = vx.read_register(MVOUT_ADDRESS, 1, 3)
        return mv_percent
    except Exception as e:
        print(f"VX: 출력량(MV) 읽기 실패: {e}")
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
        safe_output = max(0.0, min(40.0, output_percent))
        # minimalmodbus는 소수점 자릿수(1)를 인자로 전달해야 합니다.
        vx.write_register(MV_IN_ADDR, safe_output, 1, 16)
        print(f"VX: 수동 출력 설정 (주소 {MV_IN_ADDR}에 값 {safe_output} 전송)")
    except Exception as e:
        print(f"VX: 수동 출력 설정 실패: {e}")

def set_vx_sv1(vx, target_temp):
    """[함수 추가] VX의 SV-1 (D-Reg 103) 값을 설정합니다. (소수점 1자리 가정)"""
    try:
        # G.SV (D-Reg 100~199)의 소수점은 G.IN>DP-P를 따릅니다. [cite: 668]
        # 온도 읽기(PV)와 동일하게 소수점 1자리를 가정하여 SV-1 (D-Reg 103) 에 씁니다.
        vx.write_register(SV1_ADDR, target_temp, 1, 16)
        print(f"VX: SV-1 설정 (주소 {SV1_ADDR}에 값 {target_temp}°C 전송)")
    except Exception as e:
        print(f"VX: SV-1 설정 실패: {e}")

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
    STEP_OUTPUT = 5.0  # (입력) 30% 히터 출력 : 30% 출력만으로도 굉장히 높은 출력. 30%, 20%, 10%, 5% 4가지 학습
    SAMPLE_TIME_S = 1.0  # (수집) 1.0초 간격
    HEAT_DURATION_S = 50  # (시간) 50초 가열 : 80초만 가열해도 300도까지 올라감. 실험은 아무리 높아도 200도 범위 안에서 제어
    COOL_DURATION_S = 500  # (시간) 500초 (8분 20초) 냉각 : 냉각에는 긴 시간이 보통 필요.

    current_filename = f"{FILENAME_PREFIX}{int(STEP_OUTPUT)}.csv"

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

        # [안전] 현재 SV-1 값을 안전 온도로 미리 설정
        set_vx_sv1(v, SAFE_TEMP)
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
            actual_output = read_output_percent(v)
            if current_temp is None: continue
            elapsed_time = loop_start_time - start_time

            data_to_log = {
                'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Elapsed Time (s)': elapsed_time,
                'Target Output (%)': STEP_OUTPUT,
                'Actual Output (%)': actual_output,
                'Actual Temp (C)': current_temp
            }
            log_dt_data(current_filename, FIELDNAMES, data_to_log)
            print(f"가열 중... Time: {elapsed_time:.1f}s / Temp: {current_temp}°C")

            loop_time = time.time() - loop_start_time
            time.sleep(max(0, SAMPLE_TIME_S - loop_time))

        # --- [Phase 2: 자연 냉각 (Step-Down) - 수정된 로직] ---
        print(f"--- 2단계: 냉각 (AUTO 모드) 적용 ---")

        # 1. AUTO 모드로 전환 (이때 MV.BL 기능으로 높은 SV가 EEPROM에 1차 저장됨)
        set_auto_manual(v, False)
        time.sleep(0.5)

        # 2. SV-1 값을 SAFE_TEMP로 즉시 덮어쓰기 (EEPROM에 2차 저장됨)
        set_vx_sv1(v, SAFE_TEMP)
        time.sleep(0.5)

        # 3. 데이터 로깅 루프 시작
        num_cool_steps = int(COOL_DURATION_S / SAMPLE_TIME_S)

        for i in range(num_cool_steps):
            loop_start_time = time.time()

            # PV (온도)와 MV (출력)를 모두 읽음
            current_temp = read_temperature(v)
            current_output = read_output_percent(v)

            if current_temp is None or current_output is None: continue

            elapsed_time = loop_start_time - start_time

            # [중요] 'Target Output (%)'에 0.0이 아닌,
            # PID가 실제로 계산한 값(current_output, 예상값 0.0)을 기록합니다.
            data_to_log = {
                'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Elapsed Time (s)': elapsed_time,
                'Target Output (%)': 0.0,
                'Actual Output (%)': current_output,
                'Actual Temp (C)': current_temp
            }
            log_dt_data(current_filename, FIELDNAMES, data_to_log)
            print(f"냉각 중... Time: {elapsed_time:.1f}s / Temp: {current_temp}°C / Output: {current_output}%")

            loop_time = time.time() - loop_start_time
            time.sleep(max(0, SAMPLE_TIME_S - loop_time))

        print("--- 데이터 수집 완료 ---")

    except Exception as e:
        print(f"\n[메인 오류] 프로세스 중단: {e}")



    finally:
        # --- [5. 안전 종료 (수정)] ---
        if v:
            print("VX: 안전 종료 시작...")
            # 1. 히터 출력을 0%로 설정
            set_vx_manual_output(v, 0.0)  # (D-Reg 32 = 0.0)
            time.sleep(0.5)

            # 2. AUTO 모드로 복귀 (이때 SV=SAFE_TEMP 값이 EEPROM에 저장됨)
            set_auto_manual(v, False)  # (D-Reg 31 = 0)
            time.sleep(0.5)

            # 3. [중요] SV-1 값을 안전 온도로 설정
            # 'MV Bumpless' 기능으로 인해 저장될 SV 값을 안전하게 덮어씁니다.
            print(f"VX: SV 값을 안전 온도 ({SAFE_TEMP}°C)로 설정합니다.")
            set_vx_sv1(v, SAFE_TEMP)  # (D-Reg 103 = SAFE_TEMP)
            time.sleep(0.5)

            # 4. [안전] STOP 모드로 전환 (재부팅 시 자동 가열 방지)
            print("VX: STOP 모드로 전환합니다.")
            set_run_stop(v, False)  # (D-Reg 33 = 0)

            v.serial.close()
            print("VX 컨트롤러 (STOP + AUTO) 모드 복귀 및 연결 해제됨.")

    print("\n[메인 앱] 실험이 종료되어 안전 모드 복구를 호출합니다.")
    rssr()

    print("\n[메인 앱] 모든 작업이 완료되었습니다.")