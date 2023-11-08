from kivy.utils import platform
from kivy.clock import Clock


class AccHelper:
    sensorEnabled: bool = False
    x = 0
    y = 0
    z = 0
    def run(self, acc_q: asyncio.Queue) -> None:
        if platform == 'android':
            from plyer import accelerometer
            try:
                if not self.sensorEnabled:
                    accelerometer.enable()
                    Clock.schedule_interval(self.get_acceleration, 1/20)
                    self.sensorEnabled = True
                else:
                    accelerometer.disable()
                    Clock.unschedule(self.get_acceleration)
                    self.sensorEnabled = False
            except NotImplementedError:
                import traceback
                traceback.print_exc()

    def get_acceleration(self, dt):
        val = accelerometer.acceleration[:3]

        if not val == (None,None,None):
            self.x = val[0]
            self.y = val[1]
            self.z = val[2]
            self.acc_q.put_nowait(val)



