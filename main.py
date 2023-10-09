from kivymd.app import MDApp
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivy.logger import Logger
import asyncio
from plyer import gps
import datetime as dt
import json
from kivymd.icon_definitions import md_icons

from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.dropdown import DropDown
from CircularProgressBar import CircularProgressBar
from kivy_garden.mapview import MapView

from BLE import Connection, communication_manager
from ble_client_test import Debug

# kivy.version('1.9.0')

# ADDRESS, UUID = "78:21:84:9D:37:10", "0000181a-0000-1000-8000-00805f9b34fb"
ADDRESS, UUID = None, None
GPS_ON = False


class MainWindow(Screen): pass


class SecondaryWindow(Screen): pass


class WindowManager(ScreenManager): pass


class SpinnerDropdown(DropDown): pass


class Main(MDApp):
    dialog = None
    i: int = 0
    velocity: int = 0
    data: dict

    def build(self):
        """setting design for application widget development specifications on design.kv"""
        self.theme_cls.theme_style = 'Dark'
        self.theme_cls.primary_palette = 'Orange'
        self.data = {
            'Street': ['street-mode', "on_press", self.street_mode_pressed, "on_release", self.speed_dial_released],
            'Mountain': ['mountain-mode', "on_press", self.mountain_mode_pressed, "on_release",
                         self.speed_dial_released],
            'Cruise': ['cruise-mode', "on_press", self.cruise_mode_pressed, "on_release", self.speed_dial_released],
        }
        if GPS_ON:
            self.gps_time = 500  # ms´
            self.gps_info = dict()
            gps.configure(on_location=self.on_location)
            gps.start(minTime=self.gps_time)
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
        self.loading = self.root.get_screen('main_window').ids.spinner
        self.start = None
        # self.backdrop = self.root.get_screen('secondary_window').ids.backdrop

        # GPS setup and start

        # Multipe queues for app interaction between Front and Back-End
        self.slider_q = asyncio.Queue()
        self.speed_q = asyncio.Queue()
        self.drop_q = asyncio.Queue()
        self.battery_q = asyncio.Queue()
        self.angle_q = asyncio.Queue()

        self.per_button_pressed = True
        self.km_button_pressed = False

        self.angle = None

    def connect_ble(self, touch: bool) -> None:
        """Function handling BLE connection between App and ESP32"""
        if touch:
            try:
                # asyncio.create_task(run_BLE(self, self.slider_q, self.battery_q, self.drop_q))
                self.root.current = 'secondary_window'
                # asyncio.create_task(debug_BLE(self, self.slider_q, self.speed_q))
                #asyncio.create_task(self.update_battery_value())
                #asyncio.create_task(self.update_speed_value())
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
            self.slider_q.put_nowait(json.dumps({"slider": 'YES'}))
            self.root.get_screen('secondary_window').ids.adapt_slider.value = self.root.get_screen(
                'secondary_window').ids.adapt_slider.min
        else:
            self.root.get_screen('secondary_window').ids.adapt_slider.disabled = False

    def slider_slide(self, _, value: int) -> None:
        """Sends percentage of assistance wanted to ESP32
        In automatic mode: Use BATTERY and ACCELEROMETER values to determine percentage of use"""
        label = 'slider'
        if self.per_button_pressed:
            value = int(180 * value / 100)
            label = 'slider_per'
        if self.km_button_pressed:
            value = value
            label = 'slider_km'
        try:
            self.slider_q.put_nowait(json.dumps({label: value}))
        except asyncio.QueueFull:
            pass
        if value == self.root.get_screen('secondary_window').ids.adapt_slider.max:
            self.root.get_screen('secondary_window').ids.adapt_slider.hint_text_color = "red"
        else:
            self.root.get_screen('secondary_window').ids.adapt_slider.hint_text_color = "orange"

    def slider_unit_km(self, touch: bool) -> None:
        if touch:
            self.km_button_pressed = True
            self.per_button_pressed = False
            self.root.get_screen('secondary_window').ids.adapt_slider.value = 0
            self.root.get_screen('secondary_window').ids.adapt_slider.max = 20
            self.root.get_screen('secondary_window').ids.adapt_slider.step = 1
            self.root.get_screen('secondary_window').ids.adapt_slider.color = "blue"
            self.root.get_screen('secondary_window').ids.adapt_slider.thumb_color_inactive = "blue"
            self.root.get_screen('secondary_window').ids.adapt_slider.thumb_color_active = "blue"

    def slider_unit_per(self, touch: bool) -> None:
        if touch:
            self.km_button_pressed = False
            self.per_button_pressed = True
            self.root.get_screen('secondary_window').ids.adapt_slider.value = 0
            self.root.get_screen('secondary_window').ids.adapt_slider.max = 100
            self.root.get_screen('secondary_window').ids.adapt_slider.step = 5
            self.root.get_screen('secondary_window').ids.adapt_slider.color = "orange"
            self.root.get_screen('secondary_window').ids.adapt_slider.thumb_color_inactive = "orange"
            self.root.get_screen('secondary_window').ids.adapt_slider.thumb_color_active = "orange"

    def send_angle(self, touch: bool) -> None:
        if touch:
            # self.slider_q.put_nowait(json.dumps({'set_angle': self.angle}))
            print('sending angle')


    def street_mode_pressed(self, touch: bool) -> None:
        if self.start is not None:
            self.start = None
        self.start = dt.datetime.now()
        print(f'Street mode: {self.start}')

    def mountain_mode_pressed(self, touch: bool) -> None:
        if self.start is not None:
            self.start = None
        self.start = dt.datetime.now()
        print(f'Mountain mode{self.start}')

    def cruise_mode_pressed(self, touch: bool) -> None:
        if self.start is not None:
            self.start = None
        self.start = dt.datetime.now()
        print(f'Cruise mode {self.start}')

    def speed_dial_released(self, touch: bool) -> None:
        if touch:
            pressed_for = dt.datetime.now() - self.start
            print(pressed_for)
            print(pressed_for.seconds)
            if pressed_for.seconds >= 3:
                print("pressed for more than 3 secs")
        self.start = None


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
            await asyncio.sleep(0.5)

    async def update_battery_value(self) -> None:
        """Monitorss Battery life from bike"""
        max_battery_voltage = 23.7  # V //Voltage gotten when fully charged
        min_battery_voltage = 20.0  # V //Lowest voltage before battery starts getting damaged
        while True:
            print("in battery")
            try:
                current_battery_life = float(await self.battery_q.get())
                print(f'current battery: {current_battery_life}')
                battery_life = (current_battery_life - min_battery_voltage) / (
                            max_battery_voltage - min_battery_voltage)
                battery_life = int(battery_life)
                print(f"battery-> {battery_life}")
            except Exception as e:
                print(f'Exception battery:: {e}')
                battery_life = int(0)

            if battery_life > 100:
                battery_life = 100
            elif battery_life < 0:
                battery_life = 0

            self.circle_bar.set_value = battery_life
            self.circle_bar.text = f'{battery_life}%'
            await asyncio.sleep(0.5)

    async def get_angle(self) -> None:
        while True:
            try:
                self.angle = float(await self.angle_q.get())
            except Exception as e:
                self.angle = 0.0




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
