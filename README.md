# RL-temperature-controller
reinforcement learning to fine temperature control - with Hanyeong Nux
---
## Hardware Constitution
  1. Hanyeong Nux : Temperature Controller
  2. Keithley 2450 - NI : V-R-I measure and controller
  3. Window10 : Python 3.14 & Pycharm environment

## Program Tatic
 - PID controller: move from T1 to T2, where T2 > T1
 - naturally cooldown: move from T2 to T1, where T1 < T2
 - maintaining steady temperature T0 in residual temperature \epsilone = 0.1 celcious degree

## using python libraray package
 - pytorch : pip3 itall torch torchvision torchaudiio --index-url https://download.pytorch.org/whl/cu126
 - scipy, gymnasium
 - serial
 - pyvisa, pyvisa-py, pymeasure, minimalmodbus
 - numpy, pandas, seaborn, matplotlib
 - pyaml
