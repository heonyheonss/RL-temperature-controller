# 실제 제어 루프 내부 예시
from stable_baselines3 import PPO

# 모델 불러오기
model = PPO.load("ppo_heater_model")

# ... (장비 연결 코드) ...
prev_output = 0.0

while True:
    current_temp = read_temperature(v)
    target_temp = 50.0  # 목표값
    error = target_temp - current_temp

    # AI에게 현재 상태 보여주기 [오차, 현재온도, 이전출력]
    obs = np.array([error, current_temp, prev_output], dtype=np.float32)

    # AI에게 행동 물어보기
    action, _ = model.predict(obs)

    # 행동을 실제 장비 값(0~100)으로 변환
    output_percent = (action[0] + 1.0) / 2.0 * 100.0
    output_percent = max(0.0, min(100.0, output_percent))

    # 장비에 명령 전송
    set_vx_manual_output(v, output_percent)
    prev_output = output_percent

    time.sleep(1)