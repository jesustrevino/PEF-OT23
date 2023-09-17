from kivymd.app import MDApp
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivy.logger import Logger
import asyncio
from plyer import gps
from math import asin, cos, pi, sqrt

from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.dropdown import DropDown
from CircularProgressBar import CircularProgressBar
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivy_garden.mapview import MapView

from BLE import Connection, communication_manager
from ble_client_test import Debug

# kivy.version('1.9.0')

# ADDRESS, UUID = "78:21:84:9D:37:10", "0000181a-0000-1000-8000-00805f9b34fb"
ADDRESS, UUID = None, None


class MainWindow(Screen): pass


class SecondaryWindow(Screen): pass


class WindowManager(ScreenManager): pass


class SpinnerDropdown(DropDown): pass


class Main(MDApp):
    dialog = None
    i: int = 0
    velocity: int = 0

    def build(self):
        """setting design for application widget development specifications on design.kv"""
        self.theme_cls.theme_style = 'Dark'
        self.theme_cls.primary_palette = 'Orange'
        return Builder.load_file(filename='design.kv')

    async def launch_app(self):
        """Asyncronous function for kivy app start"""
        await self.async_run(async_lib='asyncio')

    async def start(self):
        """Asyncronous app making sure start is awaited as coroutine"""
        (done, pending) = await asyncio.wait({self.launch_app()}, return_when='FIRST_COMPLETED')

    def on_start(self):
        """On start method for building desired variables for later use"""
        Logger.info("Called start")
        # Renames certain components from app that will be used in other functions
        self.button = self.root.get_screen('main_window').ids.ble_button
        self.circle_bar = self.root.get_screen('secondary_window').ids.circle_progress
        self.speedmeter = self.root.get_screen('secondary_window').ids.speed
        self.speedmeter.font_size_min = self.speedmeter.font_size
        # self.backdrop = self.root.get_screen('secondary_window').ids.backdrop

        # GPS setup and start
        self.gps_time = 500 #ms
        self.gps_info = dict()
        gps.configure(on_location=self.on_location)
        gps.start(minTime=self.gps_time)

        # Multipe queues for app interaction between Front and Back-End
        self.slider_q = asyncio.Queue()
        self.speed_q = asyncio.Queue()
        self.drop_q = asyncio.Queue()
        self.battery_q = asyncio.Queue()

    def on_location(self, **kwargs):
        """callback used to gather relevant information"""
        self.i += 1
        Logger.info("Called on_location")
        Logger.info(kwargs)
        self.gps_info.update({self.i: kwargs})
        if self.i >= 1:
            self.velocity = self.calculate_speed
            self.speed_q.put_nowait(self.velocity)
            self.i = 0

    @property
    def calculate_distance(self) -> float:
        r = 6371 #radius of Earth
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
        return int(distance * 3600 / (self.gps_time / 1000)) # Multiplying by 3600 for Km/Hrs

    def show_alert(self) -> None:
        if not self.dialog:
            self.dialog = MDDialog(
                title='Connection Failed!',
                text='Failed to connect to desired device. Please select another option',
                buttons=[
                    MDFlatButton(
                        text='RETURN',
                        text_color=self.theme_cls.primary_color,
                        on_release=self.close_alert
                    )
                ]
            )
        self.dialog.open()

    def close_alert(self, obj):
        self.dialog.dismiss()

    def connect_ble(self, touch: bool) -> None:
        """Function handling BLE connection between App and ESP32"""
        if touch:
            try:
                asyncio.create_task(run_BLE(self, self.slider_q, self.battery_q, self.drop_q))
                # asyncio.create_task(debug_BLE(self, self.slider_q, self.speed_q))
                asyncio.create_task(self.update_battery_value())
            except Exception as e:
                print(e)

    def dropdown_clicked(self, _, value: str) -> None:
        """Handles events in main window dropdown"""
        asyncio.ensure_future(self.dropdown_event_handler(value))

    async def dropdown_event_handler(self, value: str) -> None:
        await self.drop_q.put(value)
        self.root.get_screen('main_window').ids.spinner.active = True

    def switch_state(self, _, value: bool) -> None:
        """Switch state for adaptive mode switch. When in adaptive mode, the slider is disabled"""
        if value:
            self.root.get_screen('secondary_window').ids.adapt_slider.disabled = True
            self.slider_q.put_nowait('YES')
            self.root.get_screen('secondary_window').ids.adapt_slider.value = self.root.get_screen(
                'secondary_window').ids.adapt_slider.min
        else:
            self.root.get_screen('secondary_window').ids.adapt_slider.disabled = False

    def slider_slide(self, _, value: int) -> None:
        """Sends percentage of assistance wanted to ESP32
        In automatic mode: Use BATTERY and ACCELEROMETER values to determine percentage of use"""
        # print(value)
        try:
            self.slider_q.put_nowait(value)
        except asyncio.QueueFull:
            pass
        # self.update_speed_value(value)
        self.update_battery_value(value)
        if value == self.root.get_screen('secondary_window').ids.adapt_slider.max:
            self.root.get_screen('secondary_window').ids.adapt_slider.hint_text_color = "red"
        else:
            self.root.get_screen('secondary_window').ids.adapt_slider.hint_text_color = "orange"

    async def update_speed_value(self) -> None:
        """Monitors current speed of bike"""
        while True:
            print("in speed")
            try:
                speed = await self.speed_q.get()
                speed = float(speed)
                print(f"speed-> {speed}")
            except Exception as e:
                print(f'Exception:: {e}')
                speed = float(0.0)
            if float(speed) > 2 * self.speedmeter.end_value / 3.6:
                pass
            else:
                self.speedmeter.set_value = speed - 25
                self.speedmeter.text = f'{int(speed)} km/h'
                # self.speedmeter.font_size = self.speedmeter.font_size_min + value

    async def update_battery_value(self) -> None:
        """Monitorss Battery life from bike

        STEPS TO DO:
            +READ FROM BLE TO UPDATE VALUE

        *for debugging purposes it shows the value from slider"""
        max_battery_voltage = 23.7 # V //Voltage gotten when fully charged
        min_battery_voltage = 20.0 # V //Lowest voltage before battery starts getting damaged
        while True:
            print("in battery")
            try:
                current_battery_life = await self.battery_q.get()
                battery_life = (current_battery_life - min_battery_voltage) / (max_battery_voltage - min_battery_voltage)
                battery_life = int(battery_life)
                print(f"battery-> {battery_life}")
            except Exception as e:
                print(f'Exception:: {e}')
                battery_life = int(0)
            if battery_life > 100:
                pass
            else:
                self.circle_bar.set_value = battery_life
                self.circle_bar.text = f'{battery_life}%'


async def debug_BLE(app: MDApp, slider_q: asyncio.Queue, speed_q: asyncio.Queue) -> None:
    app.root.get_screen('main_window').ids.spinner.active = True
    flag = asyncio.Event()
    try:
        debug = Debug(flag)
        # await debug.connected.wait()
        await debug.flag.wait()
    finally:
        print(f"flag confirmed!")
        app.root.current = 'secondary_window'
    for i in range(20):
        print(f"Other coroutine -> {i}")
        # value = await slider_q.get()
        speed_q.put_nowait(i)
        await asyncio.sleep(1)


async def run_BLE(app: MDApp, slider_q: asyncio.Queue, battery_q: asyncio.Queue, drop_q: asyncio.Queue) -> None:
    """Asyncronous connection protocol for BLE"""
    print('in run_BLE')
    read_char = "00002A3D-0000-1000-8000-00805f9b34fb"
    # write_char = "00002A58-0000-1000-8000-00805f9b34fb" ## DEPRECATED
    flag = asyncio.Event()
    connection = Connection(loop=loop,
                            uuid=UUID,
                            address=ADDRESS,
                            read_char=read_char,
                            write_char=read_char,
                            flag=flag,
                            app=app,
                            drop_q=drop_q)
    try:
        asyncio.ensure_future(connection.manager())
        asyncio.ensure_future(communication_manager(connection=connection,
                                                    write_char=read_char,
                                                    read_char=read_char,
                                                    slider_q=slider_q,
                                                    battery_q=battery_q))
        print(f"fetching connection")
        await connection.flag.wait()
        app.root.current = 'secondary_window'
        # loop.run_forever()
    finally:
        print(f"flag status confirmed!")
        print(f"speed value to send -> {battery_q}")

        # loop.run_until_complete(connection.cleanup())


if __name__ == '__main__':
    async def mainThread():
        """Creating main thread for asynchronous task definition"""
        BikeApp = Main()
        a = asyncio.create_task(BikeApp.start())
        (done, pending) = await asyncio.wait({a}, return_when='FIRST_COMPLETED')


    loop = asyncio.get_event_loop()
    asyncio.run(mainThread())
