import struct
from ctypes import create_string_buffer
from selfdrive.config import Conversions as CV
from selfdrive.car.honda.values import CAR, HONDA_BOSCH

# *** Honda specific ***
def can_cksum(mm):
  s = 0
  for c in mm:
    c = ord(c)
    s += (c>>4)
    s += c & 0xF
  s = 8-s
  s %= 0x10
  return s


def fix(msg, addr):
  msg2 = msg[0:-1] + chr(ord(msg[-1]) | can_cksum(struct.pack("I", addr)+msg))
  return msg2


def get_pt_bus(car_fingerprint, is_panda_black):
  return 1 if car_fingerprint in HONDA_BOSCH and is_panda_black else 0


def get_lkas_cmd_bus(car_fingerprint, is_panda_black):
  return 2 if car_fingerprint in HONDA_BOSCH and not is_panda_black else 0


def create_brake_command(packer, apply_brake, pump_on, pcm_override, pcm_cancel_cmd, fcw, idx, car_fingerprint, is_panda_black):
  # TODO: do we loose pressure if we keep pump off for long?
  brakelights = apply_brake > 0
  brake_rq = apply_brake > 0
  pcm_fault_cmd = False
  bus = get_pt_bus(car_fingerprint, is_panda_black)

  values = {
    "COMPUTER_BRAKE": apply_brake,
    "BRAKE_PUMP_REQUEST": pump_on,
    "CRUISE_OVERRIDE": pcm_override,
    "CRUISE_FAULT_CMD": pcm_fault_cmd,
    "CRUISE_CANCEL_CMD": pcm_cancel_cmd,
    "COMPUTER_BRAKE_REQUEST": brake_rq,
    "SET_ME_1": 1,
    "BRAKE_LIGHTS": brakelights,
    "CHIME": 0,
    # TODO: Why are there two bits for fcw? According to dbc file the first bit should also work
    "FCW": fcw << 1,
    "AEB_REQ_1": 0,
    "AEB_REQ_2": 0,
    "AEB": 0,
  }
  return packer.make_can_msg("BRAKE_COMMAND", bus, values, idx)


def create_gas_command(packer, gas_amount, idx):
  enable = gas_amount > 0.001

  values = {"ENABLE": enable}

  if enable:
    values["GAS_COMMAND"] = gas_amount * 255.
    values["GAS_COMMAND2"] = gas_amount * 255.

  return packer.make_can_msg("GAS_COMMAND", 0, values, idx)


def create_acc_commands(packer, enabled, accel, car_fingerprint, idx, is_panda_black):
  bus_pt = get_pt_bus(car_fingerprint, is_panda_black)

  commands = []

  # 0 = off
  # 5 = on
  control_on = 5 if enabled else 0

  # 0  = gas
  # 17 = no gas
  # 31 = ?!?!
  state_flag = 0 if enabled and accel > 0. else 17

  # 0 to +2000? = range
  # 720 = no gas
  # (scale from a max of 800 to 2000)
  # torque_request = (accel * 333.33) if enabled and accel > 0. else 720
  torque_request = int(accel) if enabled and accel > 0. else 720

  # 1 = brake lights and pump(?)
  # 0 = no brake
  # braking = 1 if enabled and (accel < 0.) else 0
  # # TODO: find a better way to determine if we should be braking or not. the car supports good amounts of engine braking
  braking = 1 if enabled and (accel <= -5.) else 0
  print braking
  # -1599 to +1600? = range
  # 0 = no accel
  acceleration = int(accel) if enabled else 0

  acc_control_values = {
    "FORWARD_TORQUE_CMD": torque_request,
    "STATE_FLAG": state_flag,
    "BRAKE_LIGHTS": braking,
    "BRAKE_PUMP_REQUEST": braking,
    # setting CONTROL_ON causes car to set POWERTRAIN_DATA->ACC_STATUS = 1
    "CONTROL_ON": control_on,
    "ACCEL_CMD": acceleration,
    # # TODO: check for the other cars
    "SET_TO_1": 0x01 if car_fingerprint not in (CAR.CIVIC_BOSCH) else 0x0,  # not set on civic. is this set for brake system type? starts set to 16 on car power up. drops after 1-2 seconds
  }
  commands.append(packer.make_can_msg("ACC_CONTROL", bus_pt, acc_control_values, idx))

  acc_control_on_values = {
    "SET_TO_3": 0x03,
    "CONTROL_ON": enabled,
    "SET_TO_FF": 0xff,
    "SET_TO_75": 0x75,
    "SET_TO_30": 0x30,
  }
  commands.append(packer.make_can_msg("ACC_CONTROL_ON", bus_pt, acc_control_on_values, idx))

  if car_fingerprint in (CAR.CIVIC_BOSCH):
    legacy_values = {"CHIME": 0}
    commands.append(packer.make_can_msg("LEGACY_BRAKE_COMMAND", bus_pt, legacy_values, idx))

  return commands


def create_steering_control(packer, apply_steer, lkas_active, car_fingerprint, radar_off_can, idx, is_panda_black):
  values = {
    "STEER_TORQUE": apply_steer if lkas_active else 0,
    "STEER_TORQUE_REQUEST": lkas_active,
  }
  if radar_off_can:
    bus = get_lkas_cmd_bus(car_fingerprint, is_panda_black)
  else:
    bus = get_pt_bus(car_fingerprint, is_panda_black)

  return packer.make_can_msg("STEERING_CONTROL", bus, values, idx)


def create_ui_commands(packer, pcm_speed, hud, car_fingerprint, openpilot_longitudinal_control, is_metric, idx, is_panda_black):
  commands = []
  bus_pt = get_pt_bus(car_fingerprint, is_panda_black)
  bus_lkas = get_lkas_cmd_bus(car_fingerprint, is_panda_black) if not openpilot_longitudinal_control and car_fingerprint in HONDA_BOSCH else get_pt_bus(car_fingerprint, is_panda_black)

  lkas_hud_values = {
    'SET_ME_X41': 0x41,
    'SET_ME_X48': 0x48,
    'STEERING_REQUIRED': hud.steer_required,
    'SOLID_LANES': hud.lanes,
    'BEEP': 0,
  }
  commands.append(packer.make_can_msg('LKAS_HUD', bus_lkas, lkas_hud_values, idx))

  if openpilot_longitudinal_control:
    if car_fingerprint in HONDA_BOSCH:
      # # TODO: check for the other cars
      bus_lkas = 0
      acc_hud_values = {
        'CRUISE_SPEED': hud.v_cruise,
        'ENABLE_MINI_CAR': hud.car != 0,
        'SET_TO_1': 0x01 if car_fingerprint not in (CAR.CIVIC_BOSCH) else 0x0,
        'HUD_LEAD': hud.car,
        'HUD_DISTANCE': 0x02,
        'ACC_ON': hud.car != 0,
        'IMPERIAL_UNIT_1': int(not is_metric),
        'IMPERIAL_UNIT_2': int(not is_metric),
      }
    else:
      acc_hud_values = {
        'PCM_SPEED': pcm_speed * CV.MS_TO_KPH,
        'PCM_GAS': hud.pcm_accel,
        'CRUISE_SPEED': hud.v_cruise,
        'ENABLE_MINI_CAR': hud.mini_car,
        'HUD_LEAD': hud.car,
        'HUD_DISTANCE': 3,    # max distance setting on display
        'IMPERIAL_UNIT': int(not is_metric),
        'SET_ME_X01_2': 1,
        'SET_ME_X01': 1,
      }
    commands.append(packer.make_can_msg("ACC_HUD", bus_pt, acc_hud_values, idx))

    if car_fingerprint in (CAR.CIVIC, CAR.ODYSSEY):
      radar_hud_values = {
        'ACC_ALERTS': hud.acc_alert,
        'LEAD_SPEED': 0x1fe,  # What are these magic values
        'LEAD_STATE': 0x7,
        'LEAD_DISTANCE': 0x1e,
      }
    elif car_fingerprint in HONDA_BOSCH:
      radar_hud_values = {
        # # TODO: check for the other cars
        'SET_TO_1' : 0x01 if car_fingerprint not in (CAR.CIVIC_BOSCH) else 0x0,
      }
      commands.append(packer.make_can_msg('RADAR_HUD', bus_pt, radar_hud_values, idx))

  return commands

from common.numpy_fast import clip
def create_radar_commands(v_ego, idx):
  commands = []
  v_ego_kph = clip(int(round(v_ego * CV.MS_TO_KPH)), 0, 255)
  speed = struct.pack('!B', v_ego_kph)

  msg_0x300 = ("\xf9" + speed + "\x8a\xd0" +
              ("\x20" if idx == 0 or idx == 3 else "\x00") +
              "\x00\x00")
  commands.append(make_can_msg(0x300, msg_0x300, idx, 1))

  # car_fingerprint == CAR.PILOT:
  msg_0x301 = "\x00\x00\x56\x02\x58\x00\x00"
  commands.append(make_can_msg(0x301, msg_0x301, idx, 1))

  return commands

def spam_buttons_command(packer, button_val, idx, car_fingerprint, is_panda_black):
  values = {
    'CRUISE_BUTTONS': button_val,
    'CRUISE_SETTING': 0,
  }
  bus = get_pt_bus(car_fingerprint, is_panda_black)
  return packer.make_can_msg("SCM_BUTTONS", bus, values, idx)

def create_radar_VIN_msg(radarId,radarVIN,radarCAN,radarTriggerMessage,useRadar,radarPosition,radarEpasType):
  msg_id = 0x560
  msg_len = 8
  msg = create_string_buffer(msg_len)
  if radarId == 0:
    struct.pack_into('BBBBBBBB', msg, 0, radarId, radarCAN, useRadar + (radarPosition << 1) + (radarEpasType << 3),((radarTriggerMessage >> 8) & 0xFF),(radarTriggerMessage & 0xFF),ord(radarVIN[0]),ord(radarVIN[1]),ord(radarVIN[2]))
  if radarId == 1:
    struct.pack_into('BBBBBBBB', msg, 0, radarId, ord(radarVIN[3]), ord(radarVIN[4]),ord(radarVIN[5]),ord(radarVIN[6]),ord(radarVIN[7]),ord(radarVIN[8]),ord(radarVIN[9]))
  if radarId == 2:
    struct.pack_into('BBBBBBBB', msg, 0, radarId, ord(radarVIN[10]), ord(radarVIN[11]),ord(radarVIN[12]),ord(radarVIN[13]),ord(radarVIN[14]),ord(radarVIN[15]),ord(radarVIN[16]))
  return [msg_id, 0, msg.raw, 0]
