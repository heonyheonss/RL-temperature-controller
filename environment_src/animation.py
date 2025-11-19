# 파일 이름: animation.py
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from IPython.display import HTML
import numpy as np


class TrainingAnimator:
    """
    강화학습 과정을 부드러운 '모핑(Morphing)' 애니메이션으로 생성하는 클래스
    """

    def __init__(self, recorded_data, target_temp=50.0):
        """
        recorded_data: Callback에서 수집한 리스트
        """
        self.data = recorded_data
        self.target_temp = target_temp
        self.fig = None
        self.ax1 = None
        self.ax2 = None
        self.lines = {}

    def _init_plot(self):
        """그래프 틀 생성"""
        self.fig, self.ax1 = plt.subplots(figsize=(10, 6))
        plt.close(self.fig)  # 노트북에 정적 이미지 출력 방지

        # X축 (시간)
        self.ax1.set_xlim(0, 600)
        # Y축 (온도) - 범위는 데이터에 따라 자동 조절되거나 고정
        self.ax1.set_ylim(20, 80)
        self.ax1.set_xlabel('Time (s)')
        self.ax1.set_ylabel('Temperature (°C)', color='tab:red')
        self.ax1.grid(True, alpha=0.3)

        # 보조 Y축 (히터 출력)
        self.ax2 = self.ax1.twinx()
        self.ax2.set_ylim(-5, 105)
        self.ax2.set_ylabel('Heater Output (%)', color='tab:blue')

        # 라인 객체 초기화
        self.lines['temp'], = self.ax1.plot([], [], color='tab:red', linewidth=2, label='Temperature')
        self.lines['target'], = self.ax1.plot([], [], color='black', linestyle='--', label='Target')
        self.lines['output'], = self.ax2.plot([], [], color='tab:blue', alpha=0.3, label='Output')

        # 범례
        lines = [self.lines['temp'], self.lines['target'], self.lines['output']]
        self.ax1.legend(lines, [l.get_label() for l in lines], loc='upper left')

    def _interpolate_data(self, frames_per_log):
        """
        부드러운 애니메이션을 위해 로그 데이터 사이를 보간(Interpolate)합니다.
        """
        interpolated_frames = []
        n_logs = len(self.data)

        for i in range(n_logs - 1):
            start_data = self.data[i]
            end_data = self.data[i + 1]

            # 두 데이터셋 간의 단계별 변화 생성
            for f in range(frames_per_log):
                alpha = f / frames_per_log  # 0.0 ~ 1.0 진행률

                # 선형 보간 (Linear Interpolation)
                # 온도 보간
                interp_temps = (1 - alpha) * np.array(start_data['temps']) + \
                               alpha * np.array(end_data['temps'])
                # 출력 보간
                interp_outputs = (1 - alpha) * np.array(start_data['outputs']) + \
                                 alpha * np.array(end_data['outputs'])

                # 현재 보여줄 스텝 번호 (추정)
                cur_step = int((1 - alpha) * start_data['step'] + alpha * end_data['step'])

                frame_data = {
                    'step': cur_step,
                    'times': start_data['times'],  # 시간축은 동일하다고 가정
                    'temps': interp_temps,
                    'outputs': interp_outputs
                }
                interpolated_frames.append(frame_data)

        # 마지막 데이터 추가
        interpolated_frames.append(self.data[-1])
        return interpolated_frames

    def create_morphing_video(self, frames_per_log=10, interval=50):
        """
        부드럽게 변화하는 모핑 비디오 생성
        frames_per_log: 로그 사이를 몇 개의 프레임으로 쪼갤지 (클수록 부드러움)
        interval: 프레임 간 시간 간격 (ms)
        """
        self._init_plot()

        # 데이터 보간 실행
        frames = self._interpolate_data(frames_per_log)

        def update(frame_idx):
            record = frames[frame_idx]

            times = record['times']
            temps = record['temps']
            outputs = record['outputs']
            current_step = record['step']

            # 데이터 업데이트
            self.lines['temp'].set_data(times, temps)
            self.lines['target'].set_data(times, [self.target_temp] * len(times))
            self.lines['output'].set_data(times, outputs)

            self.ax1.set_title(f'AI Learning Evolution (Morphing)\nTraining Step: {current_step}')
            return self.lines['temp'], self.lines['target'], self.lines['output']

        # 애니메이션 생성
        anim = FuncAnimation(
            self.fig,
            update,
            frames=len(frames),
            interval=interval,
            blit=False
        )

        return HTML(anim.to_jshtml())