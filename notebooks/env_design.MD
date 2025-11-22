## Custom Environment Establish
### 온도 유지 관점
 - 매 에피소드마다 새로운 target temperature array와 persist time array가 제공
 - target temperature는 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80 중에서 선별 // 예외: 시작은 항상 25가 되도록
 - persist time은 1분으로 고정
 - action space : 0 혹은 5 ~ 40 (int) "Output (%)"
 - reward :
   1) target value를 중심으로 멀어질 수 록 줄어드는 보상
   2) initial reward = 100
   3) reward = MAXIMUM reward - C1 * bounded(target - current)**2
      - because of the value of room temperature is 25, the pragmatic difference becomes 95
      - set the C1, as the total reward become zero when difference value is 95
      - nearly: 0.01108033241
   4) def bounded:
      - if current value > system allowance, return 120
      - system allowance is 120
   5) current value 와 previous value 비교,
      - t 보다 c가 높을 때, p -> c 값이 증가. : C2(Output의 크기+a)로 보상 나누기
      - t 보다 c가 낮을 때, p -> c 값이 감소. : Output이 0이 아니라면 감쇠X, Output이 0이면 보상 크기를 C3로 나눠주기 (C3는 1과 2 사이의 값)
      - c와 p의 격차가 클 수 록 보상 감쇠: C4*abs(c-p) 로 나누기
   6) target value와 current value 사이의 차가 0.5 이하일 경우:
      - achieve reward
      - 0.5 : + 5
      - 0.4 : + 6
      - 0.3 : + 7
      - 0.2 : + 8
      - 0.1 : + 9
      - 0.0 : +10
   7) previous value와 current value 가 연속해서 0.5 이하일 경우, 그 정도에 반비례하게 보상을 누적하고 싶다.
      - achieve reward * ( 0.5 + dist )
      - 만약, target value 변경 전에 + - 0.5 범위를 벗어 나면
      - 100 * abs(previous value - current value) 로 achieve reward 나누기
      - 온도를 유지한 상태로 target value 변동 혹은 프로젝트가 종료 되면 achieve reward 그대로 reward 더하기
 - reset :
    1) 방의 초기 온도를 25도로 설정
    2) 방의 이전 온도도 25도로 설정
    3) 현재 스텝 0으로
    4) max_step은 1020 # 17분(1020초)
    5) 이전 출력량 0
    6) 지연 시간(Dead Time) 버퍼
    ```
       buffer_size = int(max(1, THETA / DT))
       self.u_buffer = deque([0.0] * buffer_size, maxlen=buffer_size)
    ```
 - step :
    1) 현재 상태 결정 및 graph rendering
    2) 행동 결정 및 상태 업데이트, 보상
    3) 다음 step 
 - render :
    1) 현재의 온도를 그래프에 새로 plotting
    2) 필요하다면 스케일바 적절하게 조절