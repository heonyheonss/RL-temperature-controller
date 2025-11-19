import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import os

# --- [1. 분석할 파일 목록 설정] ---
DATA_DIR = '..\\data\\step_response'
# 수집한 CSV 파일명들을 리스트에 입력하세요.
FILE_LIST = [
    'step_response_5.csv',
    'step_response_10.csv',
    'step_response_20.csv',
    'step_response_30.csv'
]


# --- [2. FOPDT 모델 함수 정의] ---
def fopdt_model(t, Kp, tau, theta, y0, start_time):
    """
    1차 시스템 + 지연 시간 (First Order Plus Dead Time) 모델 함수
    y(t) = y0 + Kp * delta_u * (1 - exp(-(t - start_time - theta) / tau))
    (단, t < start_time + theta 일 때는 y0 유지)
    """
    # 지연 시간(theta) 적용을 위한 조건부 연산
    t_eff = t - start_time - theta
    y_pred = np.where(t_eff > 0,
                      y0 + Kp * (1 - np.exp(-t_eff / tau)),
                      y0)
    return y_pred


def analyze_step_response(filename):
    print(f"\n>> 분석 시작: {filename}")
    path_name = os.path.join(DATA_DIR, filename)

    if not os.path.exists(path_name):
        print(f"[오류] 파일을 찾을 수 없습니다: {path_name}")
        return None

    # 1. 데이터 로드
    df = pd.read_csv(path_name)

    # 2. 데이터 전처리 (가열 구간만 추출)
    # Target Output이 0보다 큰 구간만 '가열(Step Response)' 데이터로 간주
    heat_phase = df[df['Target Output (%)'] > 0.0].copy()

    if heat_phase.empty:
        print("[오류] 가열 구간 데이터를 찾을 수 없습니다.")
        return None

    # 시간 및 데이터 정규화
    # 가열 시작 시간을 0초로 맞춤
    t_data = heat_phase['Elapsed Time (s)'].values
    t_data = t_data - t_data[0]

    y_data = heat_phase['Actual Temp (C)'].values
    u_data = heat_phase['Actual Output (%)'].values  # 실제 출력값 사용

    # 3. 모델링을 위한 상수 도출
    y0 = y_data[0]  # 초기 온도
    u0 = 0.0  # 초기 입력 (0%)
    u_final = np.mean(u_data)  # 스텝 입력 크기 (평균 실제 출력)
    delta_u = u_final - u0  # 입력 변화량 (Delta U)

    print(f"   - 초기 온도(y0): {y0:.2f}°C")
    print(f"   - 평균 입력(Delta u): {delta_u:.2f}%")

    # 4. 최적화 함수 래핑 (Kp, tau, theta만 변수로 남김)
    # curve_fit은 변수가 아닌 값들은 고정시켜야 하므로 lambda나 내부 함수 사용
    # 여기서는 Kp가 scaling된 값 (Kp_real * delta_u)으로 계산되도록 식을 구성

    def fit_func(t, Kp_real, tau, theta):
        # Kp_real: 실제 공정 이득 (°C / %)
        # 이 함수는 curve_fit이 최적화할 대상입니다.
        y_model = np.where((t - theta) > 0,
                           y0 + (Kp_real * delta_u) * (1 - np.exp(-(t - theta) / tau)),
                           y0)
        return y_model

    # 5. 파라미터 추정 (Curve Fitting)
    # 초기 추정값 (Initial Guess): [Kp, tau, theta]
    # Kp ~ 3.0, tau ~ 100초, theta ~ 5초 정도로 가정하고 시작
    p0 = [3.0, 100.0, 5.0]

    # 경계값 설정 (Bounds): ((min_Kp, min_tau, min_theta), (max...))
    # Kp는 양수, tau는 양수, theta는 0 이상
    bounds = ((0.0, 1.0, 0.0), (20.0, 1000.0, 60.0))

    try:
        popt, pcov = curve_fit(fit_func, t_data, y_data, p0=p0, bounds=bounds)
        Kp_est, tau_est, theta_est = popt

        print(f"   [결과] Kp: {Kp_est:.4f} | Tau: {tau_est:.4f}s | Theta: {theta_est:.4f}s")

        # 6. 시각화 (검증용)
        plt.figure(figsize=(10, 5))
        plt.plot(t_data, y_data, 'b.', label='Measured Data', markersize=2)
        plt.plot(t_data, fit_func(t_data, *popt), 'r-',
                 label=f'FOPDT Model\n(Kp={Kp_est:.2f}, $\\tau$={tau_est:.1f}, $\\theta$={theta_est:.1f})', linewidth=2)
        plt.title(f'System ID Result: {filename}')
        plt.xlabel('Time (s)')
        plt.ylabel('Temperature (°C)')
        plt.legend()
        plt.grid(True)
        plt.savefig(f"..\\data\\fit_result_{filename.replace('.csv', '.png')}")
        print(f"   - 그래프 저장 완료: ..\\data\\fit_result_{filename.replace('.csv', '.png')}")
        # plt.show() # 필요시 주석 해제

        return {'Kp': Kp_est, 'tau': tau_est, 'theta': theta_est, 'delta_u': delta_u}

    except Exception as e:
        print(f"[오류] 파라미터 추정 실패: {e}")
        return None


# --- [실행 블록] ---
if __name__ == "__main__":
    results = []

    print("=== 시스템 식별 (FOPDT 파라미터 추출) 수행 ===\n")

    for fname in FILE_LIST:
        res = analyze_step_response(fname)
        if res:
            results.append(res)

    # --- 최종 평균 파라미터 계산 ---
    if results:
        avg_Kp = np.mean([r['Kp'] for r in results])
        avg_tau = np.mean([r['tau'] for r in results])
        avg_theta = np.mean([r['theta'] for r in results])

        final_env_parameter = {'Kp': avg_Kp, 'tau': avg_tau, 'theta': avg_theta}

        df = pd.DataFrame(final_env_parameter, index=[0])
        df.to_csv("..\\data\\final_env_parameter.csv")

        print("\n" + "=" * 50)
        print("   최종 가상환경(Digital Twin) 파라미터")
        print("=" * 50)
        print(f"1. Process Gain (Kp) : {avg_Kp:.4f} [°C / %]")
        print(f"2. Time Constant (tau): {avg_tau:.4f} [s]")
        print(f"3. Dead Time (theta)  : {avg_theta:.4f} [s]")
        print("=" * 50)
        print("※ 이 값들을 가상 환경 시뮬레이션 코드에 입력하십시오.")
    else:
        print("\n[경고] 분석할 수 있는 유효한 데이터가 없습니다.")