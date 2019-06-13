import numpy as np
from common.kalman.simple_kalman import KF1D
from selfdrive.can.parser import CANParser, CANDefine
from selfdrive.config import Conversions as CV
from selfdrive.car.rav4.values import CAR, DBC

def get_can_parser(CP):

  signals = [
    # sig_name, sig_address, default
    ("WHEEL_SPEED1", "SPEED1", 0),
    ("CRUISE_ENGAGED", "GAS2", 0),
    ("WHEEL_TORQUE", "STEER1", 0),
  ]

  checks = [
    # ("WHEEL_SPEEDS", 80),
    # ("STEER_TORQUE_SENSOR", 80),
    # ("PCM_CRUISE", 33),
  ]

  return CANParser(DBC[CP.carFingerprint]['pt'], signals, checks, 0, timeout=100)

class CarState(object):
  def __init__(self, CP):

    self.CP = CP
    self.can_define = CANDefine(DBC[CP.carFingerprint]['pt'])

    # initialize can parser
    self.car_fingerprint = CP.carFingerprint

    # vEgo kalman filter
    dt = 0.01
    # Q = np.matrix([[10.0, 0.0], [0.0, 100.0]])
    # R = 1e3
    self.v_ego_kf = KF1D(x0=[[0.0], [0.0]],
                         A=[[1.0, dt], [0.0, 1.0]],
                         C=[1.0, 0.0],
                         K=[[0.12287673], [0.29666309]])
    self.v_ego = 0.0

  def update(self, cp):
    # copy can_valid
    self.can_valid = cp.can_valid

    # update prevs, update must run once per loop
    self.prev_left_blinker_on = False
    self.prev_right_blinker_on = False

    self.door_all_closed = True
    self.seatbelt = True
    self.brake_pressed = False

    self.pedal_gas = 0
    self.car_gas = self.pedal_gas
    self.esp_disabled = False

    self.v_wheel_fl = cp.vl["SPEED1"]['WHEEL_SPEED1'] * CV.KPH_TO_MS
    self.v_wheel_fr = cp.vl["SPEED1"]['WHEEL_SPEED1'] * CV.KPH_TO_MS
    self.v_wheel_rl = cp.vl["SPEED1"]['WHEEL_SPEED1'] * CV.KPH_TO_MS
    self.v_wheel_rr = cp.vl["SPEED1"]['WHEEL_SPEED1'] * CV.KPH_TO_MS
    v_wheel = float(np.mean([self.v_wheel_fl, self.v_wheel_fr, self.v_wheel_rl, self.v_wheel_rr]))

    self.steer_torque_driver = cp.vl["STEER1"]['WHEEL_TORQUE']
    self.steer_override = abs(self.steer_torque_driver) > 11

    # Kalman filter
    if abs(v_wheel - self.v_ego) > 2.0:  # Prevent large accelerations when car starts at non zero speed
      self.v_ego_kf.x = [[v_wheel], [0.0]]

    self.v_ego_raw = v_wheel
    v_ego_x = self.v_ego_kf.update(v_wheel)
    self.v_ego = float(v_ego_x[0])
    self.a_ego = float(v_ego_x[1])
    self.standstill = not v_wheel > 0.001

    self.angle_steers = 1
    self.angle_steers_rate = 1
    can_gear = 0
    self.gear_shifter = 0
    self.main_on = bool(cp.vl["GAS2"]['CRUISE_ENGAGED'])
    self.left_blinker_on = 0
    self.right_blinker_on = 0

    # 2 is standby, 10 is active. TODO: check that everything else is really a faulty state
    self.steer_state = 0
    self.steer_error = 0
    self.ipas_active = 0
    self.brake_error = 0
    self.steer_torque_driver = 0
    self.steer_torque_motor = 0

    self.user_brake = 0
    self.v_cruise_pcm = 0
    self.pcm_acc_active = bool(cp.vl["GAS2"]['CRUISE_ENGAGED'])
    self.pcm_acc_status = self.pcm_acc_active
    self.gas_pressed = False
    self.low_speed_lockout = False
    self.brake_lights = False

    self.generic_toggle = False
