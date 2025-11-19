import os
# [해결책] OpenMP 라이브러리 중복 로드 허용 (반드시 다른 import보다 먼저 실행해야 함)
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

import torch
import torch.nn as nn
import torch.nn.functional as F

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from collections import deque
from stable_baselines3 import PPO
import matplotlib.pyplot as plt

# --- [1. 디지털 트윈 모델 (FOPDT) 정의] ---
# (이전 단계에서 식별한 파라미터 사용)
KP = 19.999
TAU = 122.544
THETA = 15.735
DT = 1.0  # 제어 주기 1초


class HeaterEnv(gym.Env):
    """
    OpenAI Gymnasium 표준을 따르는 히터 제어 환경
    """

    def __init__(self):
        super(HeaterEnv, self).__init__()

        # 1. Action Space (행동 공간): 히터 출력 0% ~ 100%
        # (학습 안정성을 위해 -1 ~ 1 사이 값으로 받고 내부에서 변환합니다)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)

        # 2. Observation Space (관측 공간): [현재오차, 현재온도, 이전출력]
        # AI가 의사결정을 하기 위해 보는 정보들입니다.
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(3,), dtype=np.float32)

        # 초기화
        self.target_temp = 50.0
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        # 상태 초기화
        self.current_temp = 24.0  # 상온 시작
        self.current_step = 0
        self.max_steps = 600  # 에피소드 당 600초 (10분) 학습

        # 지연 시간 버퍼 초기화
        buffer_size = int(max(1, THETA / DT))
        self.u_buffer = deque([0.0] * buffer_size, maxlen=buffer_size)
        self.prev_output = 0.0

        return self._get_obs(), {}

    def _get_obs(self):
        error = self.target_temp - self.current_temp
        # 정규화되지 않은 raw 값을 줍니다 (PPO가 알아서 처리함)
        return np.array([error, self.current_temp, self.prev_output], dtype=np.float32)

    def step(self, action):
        # 1. Action 변환 (-1~1 -> 0~100%)
        # tanh 등의 활성화 함수 결과가 들어오므로 범위를 맞춰줍니다.
        heater_output = (action[0] + 1.0) / 2.0 * 100.0
        heater_output = np.clip(heater_output, 0.0, 100.0)

        # 2. FOPDT 물리 시뮬레이션 (Digital Twin)
        # 지연된 입력 가져오기
        u_delayed = self.u_buffer[0]
        self.u_buffer.append(heater_output)

        # 온도 변화 계산 (오일러 적분)
        dy = (KP * u_delayed - self.current_temp + 24.0) / TAU * DT
        # (+24.0은 편차 모델을 절대 온도로 보정하기 위함)

        # 실제 식: T_new = T_old + (dt/tau) * (Kp*u - (T_old - T_ambient))
        # 식별된 모델이 (T - T_ambient) 기준이므로 위 식을 사용
        dy = (KP * u_delayed - (self.current_temp - 24.0)) / TAU * DT

        self.current_temp += dy
        self.current_step += 1
        self.prev_output = heater_output

        # 3. 보상(Reward) 계산 (가장 중요!)
        error = self.target_temp - self.current_temp

        # 기본 보상: 오차의 제곱에 페널티 (목표에 가까울수록 0에 가까움)
        reward = - (error ** 2)

        # 추가 보상: 목표 온도 근처(±0.5도)에 있으면 큰 보상
        if abs(error) < 0.5:
            reward += 10.0

        # 종료 조건
        terminated = False
        truncated = self.current_step >= self.max_steps

        return self._get_obs(), reward, terminated, truncated, {}


# --- [2. 학습 실행] ---
if __name__ == "__main__":
    # 환경 생성
    env = HeaterEnv()

    # PPO 알고리즘 모델 생성 (MlpPolicy: 다층 퍼셉트론 신경망)
    model = PPO("MlpPolicy", env, verbose=1, learning_rate=0.0003)

    print("--- 강화학습 시작 (Digital Twin) ---")
    # 20,000 스텝 학습 (약 30~40 에피소드)
    # 복잡한 제어가 아니므로 짧게 학습해도 결과가 나옵니다.
    model.learn(total_timesteps=30000)

    print("--- 학습 완료, 모델 저장 ---")
    model.save("ppo_heater_model")

    # --- [3. 학습 결과 테스트 (시뮬레이션)] ---
    print("--- 제어 성능 테스트 시작 ---")
    obs, _ = env.reset()

    times = []
    temps = []
    outputs = []

    # 테스트는 목표 온도를 변경해보며 수행
    env.target_temp = 60.0  # 목표 온도 변경

    for i in range(600):
        action, _states = model.predict(obs)
        obs, reward, done, truncated, info = env.step(action)

        # Action을 다시 0~100%로 변환하여 기록
        real_out = (action[0] + 1.0) / 2.0 * 100.0

        times.append(i)
        temps.append(obs[1])  # 관측값 중 두번째가 온도
        outputs.append(real_out)

    # 결과 시각화
    fig, ax1 = plt.subplots(figsize=(10, 6))

    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Temperature (°C)', color='red')
    ax1.plot(times, temps, color='red', label='Temperature')
    ax1.axhline(y=60.0, color='black', linestyle='--', label='Target')
    ax1.tick_params(axis='y', labelcolor='red')
    ax1.legend(loc='upper left')

    ax2 = ax1.twinx()
    ax2.set_ylabel('Heater Output (%)', color='blue')
    ax2.plot(times, outputs, color='blue', alpha=0.3, label='RL Agent Output')
    ax2.tick_params(axis='y', labelcolor='blue')

    plt.title('Reinforcement Learning Control Result (Digital Twin)')
    plt.show()