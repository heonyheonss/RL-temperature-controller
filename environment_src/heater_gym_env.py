# 파일 이름: heater_gym_env.py
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from collections import deque

# --- [시스템 파라미터] ---
# 식별된 파라미터 (사용자 환경에 맞게 수정 가능)
KP = 19.999
TAU = 122.544
THETA = 15.735
DT = 1.0  # 제어 주기 1초


class HeaterEnv(gym.Env):
    """
    FOPDT 모델 기반의 히터 제어 가상 환경
    """
    def __init__(self, target_temp=50.0):
        super(HeaterEnv, self).__init__()

        # Action: 히터 출력 (-1.0 ~ 1.0) -> 내부에서 0~100%로 변환
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(1,), dtype=np.float32)

        # Observation: [오차, 현재온도, 이전출력]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(3,), dtype=np.float32)

        self.target_temp = target_temp
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.current_temp = 25.0  # 상온
        self.prev_temp = 25.0
        self.current_step = 0
        self.max_steps = 600  # 10분(600초)

        # 지연 시간(Dead Time) 버퍼
        buffer_size = int(max(1, THETA / DT))
        self.u_buffer = deque([0.0] * buffer_size, maxlen=buffer_size)

        self.prev_output = 0.0  # 이전 스텝의 출력량 (0~100)

        return self._get_obs(), {}

    def _get_obs(self):
        error = self.target_temp - self.current_temp
        # [오차, 현재온도, 이전출력]
        return np.array([error, self.current_temp, self.prev_output], dtype=np.float32)

    def step(self, action):
        # 1. Action 변환 (-1~1 -> 0~100%)
        # PPO는 tanh 출력을 내므로 이를 물리적 범위로 변환
        raw_output = float(action[0])
        heater_output = (raw_output + 1.0) / 2.0 * 100.0
        heater_output = np.clip(heater_output, 0.0, 100.0)

        # 2. 물리 시뮬레이션 (FOPDT)
        u_delayed = self.u_buffer[0]
        self.u_buffer.append(heater_output)

        # 온도 변화 계산 (오일러 적분)
        # dy/dt = (Kp * u(t-theta) - (y - y_ambient)) / tau
        dy = (KP * u_delayed - (self.current_temp - 24.0)) / TAU * DT
        self.prev_temp = self.current_temp
        self.current_temp += dy
        self.current_step += 1

        # 3. 보상(Reward) 계산 [수정됨]
        error = self.target_temp - self.current_temp
        # (A) 오차 페널티 (기본)
        reward = - (error ** 2)
        if self.current_temp > self.target_temp + 0.5:
            reward = -1 * abs(reward)
        # (B) 제어 안정성 페널티 (Bang-Bang 제어 방지)
        # 이전 출력과 현재 출력의 차이가 클수록 감점
        delta_output = abs(heater_output - self.prev_output)
        reward -= 0.1 * delta_output
        # (C) 목표 도달 보너스 (선택)
        if abs(error) < 0.5:
            reward += 10.0

        # 상태 업데이트
        self.prev_output = heater_output

        terminated = False
        truncated = self.current_step >= self.max_steps

        return self._get_obs(), reward, terminated, truncated, {}