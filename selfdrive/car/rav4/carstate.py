import numpy as np
from common.kalman.simple_kalman import KF1D
from selfdrive.can.parser import CANParser, CANDefine
from selfdrive.config import Conversions as CV
from selfdrive.car.rav4.values import CAR, DBC

def get_can_parser(CP):

  signals = [
    # sig_name, sig_address, default
    ("WHEEL_SPEED1", "SPEED1", 0),
    ("CRUISE_INDICATOR", "GAS2", 0),
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

  def update(self, cp):
    # copy can_valid
    self.can_valid = cp.can_valid

    self.v_wheel_fl = cp.vl["SPEED1"]['WHEEL_SPEED1'] * CV.KPH_TO_MS
    self.v_wheel_fr = cp.vl["SPEED1"]['WHEEL_SPEED1'] * CV.KPH_TO_MS
    self.v_wheel_rl = cp.vl["SPEED1"]['WHEEL_SPEED1'] * CV.KPH_TO_MS
    self.v_wheel_rr = cp.vl["SPEED1"]['WHEEL_SPEED1'] * CV.KPH_TO_MS
    v_wheel = float(np.mean([self.v_wheel_fl, self.v_wheel_fr, self.v_wheel_rl, self.v_wheel_rr]))

    self.steer_torque_driver = cp.vl["STEER1"]['WHEEL_TORQUE']
    self.steer_override = abs(self.steer_torque_driver) > 11

    self.pcm_acc_active = bool(cp.vl["GAS2"]['CRUISE_INDICATOR'])
