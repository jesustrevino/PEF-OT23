from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivy.logger import Logger
import asyncio

from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.dropdown import DropDown
from CircularProgressBar import CircularProgressBar

from BLE import Connection, communication_manager
from gpshelper import GpsHelper


# ADDRESS, UUID = "78:21:84:9D:37:10", "0000181a-0000-1000-8000-00805f9b34fb"
ADDRESS, UUID = None, None
GPS_ON = True


class MainWindow(Screen): pass


class SecondaryWindow(Screen): pass


class WindowManager(ScreenManager): pass


class SpinnerDropdown(DropDown): pass


class Main(MDApp):
    dialog = None
    slider_q = asyncio.Queue()
    speed_q = asyncio.Queue()
    drop_q = asyncio.Queue()
    battery_q = asyncio.Queue()

    def build(self):
        """setting design for application widget development specifications on design.kv"""
        self.theme_cls.theme_style = 'Dark'
        self.theme_cls.primary_palette = 'Orange'
        # GPS setup and start
        if GPS_ON:
            GpsHelper().run(self.speed_q)
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

    def connect_ble(self, touch: bool) -> None:
        """Function handling BLE connection between App and ESP32"""
        if touch:
            try:
                asyncio.create_task(run_BLE(self, self.slider_q, self.battery_q, self.drop_q))
                asyncio.ensure_future(self.update_battery_value(), loop=loop)
                asyncio.ensure_future(self.update_speed_value(), loop=loop)
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
                print(f'Exception in speed:: {e}')
                speed = float(0.0)
                await asyncio.sleep(1.0)
            if float(speed) > 2 * self.speedmeter.end_value / 3.6:
                pass
            else:
                self.speedmeter.set_value = speed - 25
                self.speedmeter.text = f'{int(speed)} km/h'

    async def update_battery_value(self) -> None:
        """Monitors Battery life from bike"""
        max_battery_voltage = 23.7  # V //Voltage gotten when fully charged
        min_battery_voltage = 20.0  # V //Lowest voltage before battery starts getting damaged
        while True:
            print("in battery")
            try:
                current_battery_life = float(await self.battery_q.get())
                battery_life = (current_battery_life - min_battery_voltage) / (
                        max_battery_voltage - min_battery_voltage)
                battery_life = int(battery_life)
                print(f"battery-> {battery_life}")
            except Exception as e:
                print(f'Exception in battery:: {e}')
                battery_life = int(0)
                await asyncio.sleep(2.0)
            if battery_life > 100:
                battery_life = int(100)
            else:
                self.circle_bar.set_value = battery_life
                self.circle_bar.text = f'{battery_life}%'


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
    finally:
        print(f"flag status confirmed!")
        print(f"battery value to send -> {battery_q}")


if __name__ == '__main__':
    async def mainThread():
        """Creating main thread for asynchronous task definition"""
        BikeApp = Main()
        a = asyncio.create_task(BikeApp.start())
        (done, pending) = await asyncio.wait({a}, return_when='FIRST_COMPLETED')


    loop = asyncio.get_event_loop()
    asyncio.run(mainThread())
