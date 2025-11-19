# 파일 이름: reset_vx_to_safe_state.py

import minimalmodbus
import serial
import time

# --- 1. 장치 설정 ---
VX_PORT = 'COM3'
VX_SLAVE_ID = 1

# --- 2. Modbus 주소 ---
A_M_ADDR = 31
MV_IN_ADDR = 32
R_S_ADDR = 33
SV1_ADDR = 103

# --- 3. 안전 상태 정의 ---
SAFE_TEMP = 25.0


# --- 4. VX 제어 함수 ---
# connect_vx, set_run_stop, set_auto_manual,
# set_vx_manual_output, set_vx_sv1 함수들은
# (이전 코드와 동일하게 여기에 위치합니다)

def connect_vx(port, slave_id):
    # (이전 코드와 동일)
    print(f"Connecting to HANYOUNG VX ({port})...")
    try:
        instrument = minimalmodbus.Instrument(port, slave_id, mode='rtu')
        instrument.serial.baudrate = 9600
        instrument.serial.bytesize = 8
        instrument.serial.parity = serial.PARITY_NONE
        instrument.serial.stopbits = 1
        instrument.serial.timeout = 1.0
        print("HANYOUNG VX Connected.")
        return instrument
    except Exception as e:
        print(f"VX 연결 실패: {e}")
        return None


def set_run_stop(vx, is_run):
    # (이전 코드와 동일)
    try:
        mode_value = 1 if is_run else 0
        vx.write_register(R_S_ADDR, mode_value, 0, 16)
        status = "RUN" if is_run else "STOP"
        print(f"  -> {status} 모드 설정 완료.")
    except Exception as e:
        print(f"  -> RUN/STOP 모드 변경 실패: {e}")


def set_auto_manual(vx, is_manual):
    # (이전 코드와 동일)
    try:
        mode_value = 1 if is_manual else 0
        vx.write_register(A_M_ADDR, mode_value, 0, 16)
        status = "MANUAL" if is_manual else "AUTO"
        print(f"  -> {status} 모드 설정 완료.")
    except Exception as e:
        print(f"  -> AUTO/MANUAL 모드 변경 실패: {e}")


def set_vx_manual_output(vx, output_percent):
    # (이전 코드와 동일)
    try:
        safe_output = max(0.0, min(100.0, output_percent))
        vx.write_register(MV_IN_ADDR, safe_output, 1, 16)
        print(f"  -> 수동 출력(MV IN) {safe_output}% 설정 완료.")
    except Exception as e:
        print(f"  -> 수동 출력 설정 실패: {e}")


def set_vx_sv1(vx, target_temp):
    # (이전 코드와 동일)
    try:
        vx.write_register(SV1_ADDR, target_temp, 1, 16)
        print(f"  -> 목표 온도(SV-1) {target_temp}°C 설정 완료.")
    except Exception as e:
        print(f"  -> SV-1 설정 실패: {e}")


# --- [수정] 5. 메인 로직을 함수로 분리 ---
def run_safe_state_reset():
    """VX 컨트롤러를 안전 상태(STOP, AUTO, SV=25)로 복구합니다."""

    print("--- VX 컨트롤러 안전 상태 복구 시작 ---")
    vx_controller = None

    try:
        # 1. 컨트롤러 연결
        vx_controller = connect_vx(VX_PORT, VX_SLAVE_ID)

        if vx_controller is None:
            raise ConnectionError("컨트롤러에 연결할 수 없습니다.")

        print("\n[안전 조치 1/4] 수동 출력(MV IN)을 0.0%로 설정합니다...")
        set_vx_manual_output(vx_controller, 0.0)
        time.sleep(0.5)

        print(f"\n[안전 조치 2/4] 목표 온도(SV-1)를 {SAFE_TEMP}°C로 설정합니다...")
        set_vx_sv1(vx_controller, SAFE_TEMP)
        time.sleep(0.5)

        print("\n[안전 조치 3/4] 제어 모드를 AUTO로 전환합니다...")
        set_auto_manual(vx_controller, False)  # False = AUTO
        time.sleep(0.5)

        print("\n[안전 조치 4/4] 작동 상태를 STOP으로 전환합니다...")
        set_run_stop(vx_controller, False)  # False = STOP
        time.sleep(0.5)

        print("\n--- 모든 설정값이 안전 상태로 복구되었습니다. ---")

    except Exception as e:
        print(f"\n[오류 발생] 안전 모드 복구 실패: {e}")

    finally:
        # 6. 연결 해제
        if vx_controller:
            vx_controller.serial.close()
            print("\nVX 컨트롤러 연결이 해제되었습니다.")


# --- [수정] 6. 직접 실행 시 메인 함수 호출 ---
if __name__ == "__main__":
    run_safe_state_reset()  # 이 파일만 단독 실행 시 이 함수가 호출됨