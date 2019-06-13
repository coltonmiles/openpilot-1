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
  def compute_gb(accel, speed):
    return float(accel) / 3.0

  @staticmethod
  def calc_accel_override(a_ego, a_target, v_ego, v_target):
    return 1.0

  @staticmethod
  def get_params(candidate, fingerprint, vin=""):

    ret = car.CarParams.new_message()
    ret.carName = "rav4"
    ret.carFingerprint = candidate
    ret.carVin = vin

    ret.safetyModel = car.CarParams.SafetyModels.noOutput

    # pedal
    ret.enableCruise = not ret.enableGasInterceptor

    # FIXME: hardcoding honda civic 2016 touring params so they can be used to
    # scale unknown params for other cars
    mass_civic = 2923 * CV.LB_TO_KG + std_cargo
    wheelbase_civic = 2.70
    centerToFront_civic = wheelbase_civic * 0.4
    centerToRear_civic = wheelbase_civic - centerToFront_civic
    rotationalInertia_civic = 2500
    tireStiffnessFront_civic = 192150
    tireStiffnessRear_civic = 202500

    ret.steerActuatorDelay = 0.12  # Default delay, Prius has larger delay

    stop_and_go = True
    ret.safetyParam = 66  # see conversion factor for STEER_TORQUE_EPS in dbc file
    ret.wheelbase = 2.70
    ret.steerRatio = 15.00   # unknown end-to-end spec
    tire_stiffness_factor = 0.6371   # hand-tune
    ret.mass = 3045 * CV.LB_TO_KG + std_cargo

    ret.lateralTuning.init('indi')
    ret.lateralTuning.indi.innerLoopGain = 4.0
    ret.lateralTuning.indi.outerLoopGain = 3.0
    ret.lateralTuning.indi.timeConstant = 1.0
    ret.lateralTuning.indi.actuatorEffectiveness = 1.0

    ret.steerActuatorDelay = 0.5
    ret.steerRateCost = 0.5

    ret.steerRateCost = 1.
    ret.centerToFront = ret.wheelbase * 0.44

    #detect the Pedal address
    ret.enableGasInterceptor = False

    # min speed to enable ACC. if car can do stop and go, then set enabling speed
    # to a negative value, so it won't matter.
    ret.minEnableSpeed = -1.

    centerToRear = ret.wheelbase - ret.centerToFront
    # TODO: get actual value, for now starting with reasonable value for
    # civic and scaling by mass and wheelbase
    ret.rotationalInertia = rotationalInertia_civic * \
                            ret.mass * ret.wheelbase**2 / (mass_civic * wheelbase_civic**2)

    # TODO: start from empirically derived lateral slip stiffness for the civic and scale by
    # mass and CG position, so all cars will have approximately similar dyn behaviors
    ret.tireStiffnessFront = (tireStiffnessFront_civic * tire_stiffness_factor) * \
                             ret.mass / mass_civic * \
                             (centerToRear / ret.wheelbase) / (centerToRear_civic / wheelbase_civic)
    ret.tireStiffnessRear = (tireStiffnessRear_civic * tire_stiffness_factor) * \
                            ret.mass / mass_civic * \
                            (ret.centerToFront / ret.wheelbase) / (centerToFront_civic / wheelbase_civic)

    # no rear steering, at least on the listed cars above
    ret.steerRatioRear = 0.
    ret.steerControlType = car.CarParams.SteerControlType.torque

    # steer, gas, brake limitations VS speed
    ret.steerMaxBP = [16. * CV.KPH_TO_MS, 45. * CV.KPH_TO_MS]  # breakpoints at 1 and 40 kph
    ret.steerMaxV = [1., 1.]  # 2/3rd torque allowed above 45 kph
    ret.brakeMaxBP = [5., 20.]
    ret.brakeMaxV = [1., 0.8]

    ret.openpilotLongitudinalControl = False

    ret.steerLimitAlert = False

    ret.longitudinalTuning.deadzoneBP = [0., 9.]
    ret.longitudinalTuning.deadzoneV = [0., .15]
    ret.longitudinalTuning.kpBP = [0., 5., 35.]
    ret.longitudinalTuning.kiBP = [0., 35.]
    ret.stoppingControl = False
    ret.startAccel = 0.0

    if ret.enableGasInterceptor:
      ret.gasMaxBP = [0., 9., 35]
      ret.gasMaxV = [0.2, 0.5, 0.7]
      ret.longitudinalTuning.kpV = [1.2, 0.8, 0.5]
      ret.longitudinalTuning.kiV = [0.18, 0.12]
    else:
      ret.gasMaxBP = [0.]
      ret.gasMaxV = [0.5]
      ret.longitudinalTuning.kpV = [3.6, 2.4, 1.5]
      ret.longitudinalTuning.kiV = [0.54, 0.36]

    return ret

  # returns a car.CarState
  def update(self, c):
    # ******************* do can recv *******************
    canMonoTimes = []

    can_valid, _ = self.cp.update(int(sec_since_boot() * 1e9), True)
    can_rcv_error = not can_valid

    self.CS.update(self.cp)

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
