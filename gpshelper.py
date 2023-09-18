from kivy.utils import platform
from kivymd.uix.dialog import MDDialog
import asyncio
from math import asin, cos, pi, sqrt

class GpsHelper:
    gps_time: int = 1000
    gps_min_distance: int = 0
    gps_info: dict = dict()
    i: int = 0
    velocity: int = 0
    def run(self, speed_q: asyncio.Queue):
        # Get reference
        self.speed_q = speed_q

        # Request permissions on Android
        if platform == 'android':
            from android.permissions import Permission, request_permissions
            def callback(permission, results):
                if all([res for res in results]):
                    print('Got all permissions')
                else:
                    print('Did not get all permissions')
            request_permissions([Permission.ACCESS_COARSE_LOCATION, Permission.ACCESS_FINE_LOCATION,
                                 callback])

        # configure GPS
        if platform == 'android' or platform == 'ios':
            from plyer import gps
            gps.configure(on_location=self.on_location,
                          on_status=self.on_auth_status)
            gps.start(minTime=self.gps_time, minDistance=self.gps_min_distance)

    def on_location(self, *args, **kwargs):
        """callback used to gather relevant information"""
        self.i += 1
        self.gps_info.update({self.i: {kwargs['lat'], kwargs['lon']}})
        if self.i >= 1:
            self.velocity = self.calculate_speed
            self.speed_q.put_nowait(self.velocity)
            self.i = 0

    @property
    def calculate_distance(self) -> float:
        r = 6371  # radius of Earth
        p = pi / 180  # multiply this to convert Degrees to Radians
        lat1 = self.gps_info[0]["lat"]
        lon1 = self.gps_info[0]["lon"]
        lat2 = self.gps_info[1]["lat"]
        lon2 = self.gps_info[1]["lon"]
        # CHECK HAVERSINE FORMULA
        return 2 * r * asin(
            sqrt(0.5 - cos((lat2 - lat1) * p) / 2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2))

    @property
    def calculate_speed(self) -> int:
        # For current speed a & b will be first & second values on list
        # For average speed it will be first & last values
        distance = self.calculate_distance
        return int(distance * 3600 / (self.gps_time / 1000))  # Multiplying by 3600 for Km/Hrs

    def on_auth_status(self, general_status: str, status_message: str) -> None:
        if general_status == 'provider-enabled':
            pass
        else:
            self.open_gps_access_popup()

    def open_gps_access_popup(self) -> None:
        dialog = MDDialog(title='GPS Error',
                          text="You need to enable GPS access for the app to function properly")
        dialog.size_hint = [0.8,0.8]
        dialog.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        dialog.open()
