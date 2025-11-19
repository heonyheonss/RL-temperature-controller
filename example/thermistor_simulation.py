import numpy as np
import matplotlib.pyplot as plt

# ==========================================================
# 1. 시뮬레이션 파라미터 설정
# ==========================================================

# 온도 범위 설정: 25°C ~ 70°C (논문에서 제시된 생체/웨어러블 측정 범위)
T_celsius = np.linspace(25, 75, 200)
T_kelvin = T_celsius + 273.15
T25_kelvin = 25 + 273.15

# ---  상용 대표 샘플 (Commercial Representative) ---
# 모델: Murata NCP15XH103F03RC
# 출처: Murata Datasheet [17]
R25_comm = 10000.0      # 10 kOhm (표준 저항)
B_comm = 3380.0         # B-value (25/50°C)

# ---  연구용 대표 샘플 (Research Representative) ---
# 모델: m-LRS NiO Sensor (50um Channel Width)
# 출처: Shin et al. (2019) - Supp Info Table S1
# 특징: 가장 높은 감도를 보인 샘플 선정
R25_res = 8.8 * 10**6   # 8.8 MOhm (높은 임피던스)
B_res = 7650.0          # B-value (초고감도)

# ==========================================================
# 2. 저항 계산 함수 (Beta Parameter Equation)
# R(T) = R25 * exp( B * (1/T - 1/T25) )
# ==========================================================

def calculate_ntc_resistance(T_k, R25, B, T25_k):
    """
    NTC 서미스터의 온도별 저항값을 계산합니다.
    T_k: 절대 온도 배열 (Kelvin)
    R25: 25도에서의 기준 저항 (Ohm)
    B: B-상수 (Kelvin)
    T25_k: 25도의 절대 온도 (Kelvin)
    """
    return R25 * np.exp(B * (1/T_k - 1/T25_k))

# 각 샘플의 저항값 계산
R_comm_vals = calculate_ntc_resistance(T_kelvin, R25_comm, B_comm, T25_kelvin)
R_res_vals = calculate_ntc_resistance(T_kelvin, R25_res, B_res, T25_kelvin)

# 정규화된 저항 (Normalized Resistance, R / R25)
# - 초기 저항값이 다르므로 감도(기울기)를 직접 비교하기 위해 사용
R_norm_comm = R_comm_vals / R25_comm
R_norm_res = R_res_vals / R25_res

# ==========================================================
# 3. 그래프 시각화
# ==========================================================

plt.style.use('seaborn-v0_8-darkgrid') # 스타일 설정 (matplotlib 버전에 따라 다를 수 있음)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# [그래프 1] 절대 저항값 비교 (Log Scale)
# - 임피던스 레벨의 거대한 차이를 보여줌 (kOhm vs MOhm)
ax1.plot(T_celsius, R_comm_vals, label=f'Commercial (Murata): 10 k$\\Omega$, B={int(B_comm)}K',
         color='navy', linewidth=2.5)
ax1.plot(T_celsius, R_res_vals, label=f'Research (m-LRS NiO): 8.8 M$\\Omega$, B={int(B_res)}K',
         color='crimson', linewidth=2.5)

ax1.set_yscale('log') # 로그 스케일 적용
ax1.set_title('Absolute Resistance vs. Temperature (Log Scale)', fontsize=14, fontweight='bold')
ax1.set_xlabel('Temperature (°C)', fontsize=12)
ax1.set_ylabel('Resistance ($\\Omega$)', fontsize=12)
ax1.grid(True, which="both", ls="-", alpha=0.3)
ax1.legend(fontsize=11, loc='upper right', frameon=True)

# [그래프 2] 정규화 저항 비교 (Sensitivity Comparison)
# - B-value 차이에 따른 저항 변화율(기울기) 차이를 보여줌
ax2.plot(T_celsius, R_norm_comm, label=f'Commercial (B={int(B_comm)}K)',
         color='navy', linestyle='--', linewidth=2.5)
ax2.plot(T_celsius, R_norm_res, label=f'Research (B={int(B_res)}K)',
         color='crimson', linewidth=2.5)

ax2.set_title('Normalized Resistance ($R/R_{25}$) vs. Temperature', fontsize=14, fontweight='bold')
ax2.set_xlabel('Temperature (°C)', fontsize=12)
ax2.set_ylabel('Normalized Resistance ($R/R_{25}$)', fontsize=12)
ax2.grid(True, which="major", ls="-", alpha=0.3)
ax2.legend(fontsize=11, loc='upper right', frameon=True)

# 50도에서의 감도 차이 주석 추가
idx_50 = np.abs(T_celsius - 50).argmin()
val_50_comm = R_norm_comm[idx_50]
val_50_res = R_norm_res[idx_50]

# 화살표 및 텍스트 주석
ax2.annotate(f'Comm at 50°C: {val_50_comm:.2f}x',
             xy=(50, val_50_comm), xytext=(55, val_50_comm + 0.15),
             arrowprops=dict(facecolor='navy', shrink=0.05), fontsize=10, color='navy')

ax2.annotate(f'Research at 50°C: {val_50_res:.2f}x\n(Much Steeper Drop)',
             xy=(50, val_50_res), xytext=(30, val_50_res - 0.15),
             arrowprops=dict(facecolor='crimson', shrink=0.05), fontsize=10, color='crimson')

plt.suptitle('Comparative Analysis: Commercial vs. Research NTC Thermistor Characteristics',
             fontsize=16, y=1.02)
plt.tight_layout()
plt.show()

print("Note: The research sample shows a much steeper slope in the normalized graph,")
print("indicating significantly higher sensitivity (B-value) compared to the commercial standard.")