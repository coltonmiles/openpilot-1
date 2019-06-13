#!/usr/bin/env python
from common.realtime import sec_since_boot
from cereal import car
from selfdrive.config import Conversions as CV
from selfdrive.controls.lib.drive_helpers import EventTypes as ET, create_event
from selfdrive.controls.lib.vehicle_model import VehicleModel
from selfdrive.car.rav4.carstate import CarState, get_can_parser
from selfdrive.car.rav4.values import CAR
from selfdrive.swaglog import cloudlog


class CarInterface(object):
  def __init__(self, CP, CarController):
    self.CP = CP
    self.VM = VehicleModel(CP)

    self.frame = 0
    self.can_invalid_count = 0
    self.cruise_enabled_prev = False

    # *** init the major players ***
    self.CS = CarState(CP)

    self.cp = get_can_parser(CP)

    self.CC = None
    if CarController is not None:
      self.CC = CarController(self.cp.dbc_name, CP.carFingerprint)

  @staticmethod
  def get_params(candidate, fingerprint, vin=""):


    ret = car.CarParams.new_message()

    ret.carName = "rav4"
    ret.carFingerprint = candidate

    ret.safetyModel = car.CarParams.SafetyModels.noOutput

    return ret

  # returns a car.CarState
  def update(self, c):
    # ******************* do can recv *******************
    canMonoTimes = []

    can_valid, _ = self.cp.update(int(sec_since_boot() * 1e9), True)
    can_rcv_error = not can_valid

    self.CS.update(self.cp, self.cp_cam)

    # create message
    ret = car.CarState.new_message()

    # speeds
    ret.wheelSpeeds.fl = self.CS.v_wheel_fl
    ret.wheelSpeeds.fr = self.CS.v_wheel_fr
    ret.wheelSpeeds.rl = self.CS.v_wheel_rl
    ret.wheelSpeeds.rr = self.CS.v_wheel_rr

    ret.steeringTorque = self.CS.steer_torque_driver
    ret.steeringPressed = self.CS.steer_override

    # cruise state
    ret.cruiseState.enabled = self.CS.pcm_acc_active

    # events
    events = []
    if not self.CS.can_valid:
      self.can_invalid_count += 1
    else:
      self.can_invalid_count = 0

    # if ret.doorOpen:
    #   events.append(create_event('doorOpen', [ET.NO_ENTRY, ET.SOFT_DISABLE]))
    # if ret.seatbeltUnlatched:
    #   events.append(create_event('seatbeltNotLatched', [ET.NO_ENTRY, ET.SOFT_DISABLE]))

    ret.events = events
    ret.canMonoTimes = canMonoTimes

    self.cruise_enabled_prev = ret.cruiseState.enabled

    return ret.as_reader()

  # pass in a car.CarControl
  # to be called @ 100hz
  def apply(self, c):

    can_sends = self.CC.update(c.enabled, self.CS, self.frame,
                               c.actuators)

    self.frame += 1
    return can_sends
