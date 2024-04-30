import olympe
import os
from olympe.messages.ardrone3.Piloting import TakeOff, Landing, moveBy
from olympe.messages.ardrone3.PilotingState import (
    PositionChanged,
    SpeedChanged,
    AttitudeChanged,
    AltitudeAboveGroundChanged,
    AlertStateChanged,
    FlyingStateChanged,
    NavigateHomeStateChanged,
)
from olympe.messages.camera2.Command import GetState
import time
import logness


logness.update_config({
    "handlers": {
        "olympe_log_file": {
            "class": "logness.FileHandler",
            "formatter": "default_formatter",
            "filename": "olympe.log"
        },
        "ulog_log_file": {
            "class": "logness.FileHandler",
            "formatter": "default_formatter",
            "filename": "ulog.log"
        },
    },
    "loggers": {
        "olympe": {
            "handlers": ["olympe_log_file"]
        },
        "ulog": {
            "level": "DEBUG",
            "handlers": ["ulog_log_file"],
        }
    }
})



# olympe.log.update_config({"loggers": {"olympe": {"level": "INFO"}}})

DRONE_IP = os.environ.get("DRONE_IP", "10.202.0.1")


def print_event(event):
    # Here we're just serializing an event object and truncate the result if necessary
    # before printing it.
    if isinstance(event, olympe.ArsdkMessageEvent):
        max_args_size = 60
        args = str(event.args)
        args = (args[: max_args_size - 3] + "...") if len(args) > max_args_size else args
        print(f"{event.message.fullName}({args})")
    else:
        print(str(event))


# This is the simplest event listener. It just exposes one
# method that matches every event message and prints it.
class EveryEventListener(olympe.EventListener):
    @olympe.listen_event()
    def onAnyEvent(self, event, scheduler):
        print_event(event)


# olympe.EventListener implements the visitor pattern.
# You should use the `olympe.listen_event` decorator to
# select the type(s) of events associated with each method
class FlightListener(olympe.EventListener):

    # This set a default queue size for every listener method
    default_queue_size = 100

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.takeoff_count = 0

    @olympe.listen_event(AltitudeAboveGroundChanged(_policy="wait"))
    def onAltitudeAboveGroundChanged(self, event, scheduler):
        print("height above ground = {altitude}".format(**event.args))

    @olympe.listen_event(queue_size=100)
    def default(self, event, scheduler):
        pass
        # print_event(event)


def test_listener():
    drone = olympe.Drone(DRONE_IP)
    # Explicit subscription to every event
    every_event_listener = EveryEventListener(drone)
    every_event_listener.subscribe()
    drone.connect()
    every_event_listener.unsubscribe()

    # You can also subscribe/unsubscribe automatically using a with statement
    with FlightListener(drone) as flight_listener:

        get_state = drone(GetState(camera_id=0)).wait()
        assert get_state.success()
        assert drone(
            FlyingStateChanged(state="hovering")
            | (TakeOff() & FlyingStateChanged(state="hovering"))
        ).wait(5).success()
        time.sleep(5)

        drone(Landing()).wait()

        print(f"Takeoff count = {flight_listener.takeoff_count}")
        drone.disconnect()


if __name__ == "__main__":
    test_listener()
