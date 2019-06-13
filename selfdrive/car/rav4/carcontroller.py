from cereal import car
from common.numpy_fast import clip, interp
from selfdrive.can.packer import CANPacker

# VisualAlert = car.CarControl.HUDControl.VisualAlert
# AudibleAlert = car.CarControl.HUDControl.AudibleAlert

# def process_hud_alert(hud_alert, audible_alert):
#   # initialize to no alert
#   steer = 0
#   fcw = 0
#   sound1 = 0
#   sound2 = 0
#
#   if hud_alert == VisualAlert.fcw:
#     fcw = 1
#   elif hud_alert == VisualAlert.steerRequired:
#     steer = 1
#
#   if audible_alert == AudibleAlert.chimeWarningRepeat:
#     sound1 = 1
#   elif audible_alert != AudibleAlert.none:
#     # TODO: find a way to send single chimes
#     sound2 = 1
#
#   return steer, fcw, sound1, sound2

class CarController(object):
  def __init__(self, dbc_name, car_fingerprint):
    self.braking = False
    # redundant safety check with the board
    self.controls_allowed = True
    self.car_fingerprint = car_fingerprint
    # self.alert_active = False

    self.packer = CANPacker(dbc_name)

  def update(self, enabled, CS, frame, actuators):

    can_sends = []

    # # ui mesg is at 100Hz but we send asap if:
    # # - there is something to display
    # # - there is something to stop displaying
    # alert_out = process_hud_alert(hud_alert, audible_alert)
    # steer, fcw, sound1, sound2 = alert_out
    #
    # if (any(alert_out) and not self.alert_active) or \
    #    (not any(alert_out) and self.alert_active):
    #   send_ui = True
    #   self.alert_active = not self.alert_active
    # else:
    #   send_ui = False

    return can_sends
