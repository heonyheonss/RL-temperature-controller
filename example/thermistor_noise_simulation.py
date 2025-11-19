import numpy as np
import matplotlib.pyplot as plt


# ==========================================================
# 1. 노이즈 생성 함수 정의
# ==========================================================

def generate_johnson_noise(R, T_kelvin, bandwidth, num_samples):
    """
    존슨-나이퀴스트 열잡음(White Noise) 생성
    V_rms = sqrt(4 * kB * T * R * Bandwidth)
    """
    kb = 1.38e-23  # 볼츠만 상수
    v_rms = np.sqrt(4 * kb * T_kelvin * R * bandwidth)
    # 정규분포(가우시안)를 따르는 노이즈 생성
    noise = np.random.normal(0, v_rms, num_samples)
    return noise, v_rms


def generate_pink_noise(num_samples):
    """
    1/f 노이즈(Pink Noise) 근사 생성
    - 백색 잡음의 스펙트럼을 필터링하여 생성
    """
    white = np.random.randn(num_samples)
    fft_white = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(num_samples)

    # 1/f 스펙트럼 적용 (f=0 제외)
    # scaling factor = 1 / sqrt(f)
    scale = np.ones_like(freqs)
    scale[1:] = 1 / np.sqrt(freqs[1:])

    fft_pink = fft_white * scale
    pink = np.fft.irfft(fft_pink)

    # 크기 정규화 (표준편차를 1로 맞춤)
    pink = pink / np.std(pink)
    return pink


# ==========================================================
# 2. 시뮬레이션 설정
# ==========================================================

# 시간 설정
fs = 100  # 샘플링 레이트 (Hz)
duration = 2.0  # 측정 시간 (초)
t = np.linspace(0, duration, int(fs * duration))
N = len(t)

# 환경 설정
T_target_c = 37.0  # 목표 측정 온도 (체온)
T_target_k = T_target_c + 273.15
bandwidth = 50  # 측정 대역폭 (Hz)

# 센서 스펙 (이전 데이터 활용)
# [상용] Murata 10k
R25_comm = 10000.0
B_comm = 3380.0
# [연구용] m-LRS NiO
R25_res = 8.8 * 10 ** 6  # 8.8 MOhm
B_res = 7650.0
T25_k = 298.15


# ==========================================================
# 3. 신호 및 노이즈 계산
# ==========================================================

def get_R_and_Sensitivity(R25, B, T_k):
    """특정 온도에서의 저항값(R)과 감도(dR/dT) 계산"""
    R = R25 * np.exp(B * (1 / T_k - 1 / T25_k))
    # 감도 dR/dT = R * (-B / T^2)
    sensitivity = R * (-B / (T_k ** 2))
    return R, sensitivity


# 3.1 기본 물리량 계산
R_comm, S_comm = get_R_and_Sensitivity(R25_comm, B_comm, T_target_k)
R_res, S_res = get_R_and_Sensitivity(R25_res, B_res, T_target_k)

# 3.2 노이즈 전압 생성
# (1) 열잡음 (Johnson Noise)
noise_v_comm_w, v_rms_comm = generate_johnson_noise(R_comm, T_target_k, bandwidth, N)
noise_v_res_w, v_rms_res = generate_johnson_noise(R_res, T_target_k, bandwidth, N)

# (2) 1/f 노이즈 (Pink Noise)
# 연구용 센서는 입자 기반이므로 1/f 노이즈가 더 크다고 가정 (상대적 크기 계수 적용)
flicker_factor_comm = 0.5  # 상용 센서 플리커 계수 (임의 단위)
flicker_factor_res = 5.0  # 연구용 센서 (구조적 결함 가정, 10배 높게 설정)

noise_v_comm_p = generate_pink_noise(N) * v_rms_comm * flicker_factor_comm
noise_v_res_p = generate_pink_noise(N) * v_rms_res * flicker_factor_res

# 총 전압 노이즈
total_noise_v_comm = noise_v_comm_w + noise_v_comm_p
total_noise_v_res = noise_v_res_w + noise_v_res_p


# 3.3 노이즈를 온도로 환산 (Noise Equivalent Temperature)
# dT = dV / (dV/dT)... 전압 분배 회로 가정 시 복잡하므로
# 여기서는 저항 노이즈로 바로 환산: dR_noise = V_noise / I_bias 가정보다,
# 단순화하여 dT_error = V_noise_eff / (Sensitivity_Voltage) 대신
# 저항 변화율로 접근: dR/R = V_noise / V_signal (비례)
# 가장 정확한 방법: dT = dR / (dR/dT)
# dR은 열잡음 전압에 의해 유발된 등가 저항 흔들림으로 간주 (V_noise / I_bias)
# 편의상 1V 인가 전압 분배 회로(R_series = R_thermistor)를 가정했을 때의 출력 전압 노이즈로 변환

def voltage_divider_sensitivity(V_in, R, B, T):
    """전압 분배 회로의 온도 감도 (Volts/K)"""
    # V_out = V_in * R / (R + R) = V_in / 2 (매칭 저항 사용 시)
    # dV_out/dT = V_in * (dR/dT * R - R * dR/dT) / (R+R)^2... 이 아니라
    # dV_out/dT = V_in * (R_series * dR/dT) / (R + R_series)^2
    # R_series = R (매칭) 일 때, = V_in * (R * dR/dT) / (2R)^2 = V_in * (dR/dT) / 4R
    # dR/dT = -R * B / T^2 이므로
    # dV_out/dT = V_in * (-R * B / T^2) / 4R = - V_in * B / (4 * T^2)
    return abs(V_in * B / (4 * T ** 2))


V_supply = 3.3  # 3.3V 구동 가정

# 전압 감도 (Volts / degC)
Sens_V_comm = voltage_divider_sensitivity(V_supply, R_comm, B_comm, T_target_k)
Sens_V_res = voltage_divider_sensitivity(V_supply, R_res, B_res, T_target_k)

# 전압 노이즈를 온도 오차로 변환 (NET: Noise Equivalent Temperature)
# 전압 노이즈가 분배 회로 출력단에서 감쇄되는 비율은 무시하고 최악의 경우(Sensor 자체 노이즈)로 비교
# 실제로는 임피던스 매칭 때문에 노이즈 전압도 회로에 따라 달라지지만,
# 여기서는 '센서 자체의 열잡음 전압'이 곧바로 신호에 더해진다고 가정하고 감도로 나눔
Temp_error_comm = total_noise_v_comm / Sens_V_comm
Temp_error_res = total_noise_v_res / Sens_V_res

# ==========================================================
# 4. 결과 시각화
# ==========================================================

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

# [그래프 1] 시뮬레이션된 온도 측정 노이즈 (시간 영역)
ax1.plot(t, Temp_error_comm, label=f'Commercial (10k$\\Omega$)\nJohnson Noise RMS: {v_rms_comm * 1e6:.2f} $\\mu$V',
         color='navy', alpha=0.8)
ax1.plot(t, Temp_error_res, label=f'Research (8.8M$\\Omega$)\nJohnson Noise RMS: {v_rms_res * 1e6:.2f} $\\mu$V',
         color='crimson', alpha=0.7)
ax1.set_title(f'Simulated Temperature Fluctuation due to Natural Noise (@ {T_target_c}°C)', fontsize=14,
              fontweight='bold')
ax1.set_ylabel('Temperature Error (°C)', fontsize=12)
ax1.legend(loc='upper right', fontsize=10)
ax1.grid(True, which='both', alpha=0.3)

# [그래프 2] 노이즈 성분 비교 (확대)
# 연구용 센서의 오차가 너무 커서 상용 센서가 안 보일 수 있으므로 y축 범위 제한 또는 별도 표기 필요하지만
# 여기서는 그대로 보여주어 차이를 강조
ax2.plot(t, Temp_error_comm, color='navy', label='Commercial')
ax2.set_title('Zoom-in: Commercial Sensor Noise Level', fontsize=14, fontweight='bold')
ax2.set_ylabel('Temperature Error (°C)', fontsize=12)
ax2.set_xlabel('Time (seconds)', fontsize=12)
ax2.legend()
ax2.grid(True, alpha=0.3)

# 통계 출력
print(f"--- Simulation Results at {T_target_c}°C ---")
print(f" Resistance: {R_comm / 1000:.2f} kΩ")
print(f"  - Sensitivity: {Sens_V_comm * 1000:.2f} mV/°C")
print(f"  - Noise RMS (Voltage): {np.std(total_noise_v_comm) * 1e6:.2f} µV")
print(f"  - Noise Equivalent Temp (NET): {np.std(Temp_error_comm):.5f} °C")
print(f"\n Resistance: {R_res / 1e6:.2f} MΩ")
print(f"  - Sensitivity: {Sens_V_res * 1000:.2f} mV/°C")
print(f"  - Noise RMS (Voltage): {np.std(total_noise_v_res) * 1e6:.2f} µV")
print(f"  - Noise Equivalent Temp (NET): {np.std(Temp_error_res):.5f} °C")
print(f"\n[Analysis]")
print(f"Research sensor has {Sens_V_res / Sens_V_comm:.1f}x higher sensitivity (Signal),")
print(f"but {np.std(total_noise_v_res) / np.std(total_noise_v_comm):.1f}x higher noise floor.")
print(f"This results in a Signal-to-Noise Ratio (SNR) penalty.")

plt.tight_layout()
plt.show()