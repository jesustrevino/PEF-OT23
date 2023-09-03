from kivymd.app import MDApp
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
import asyncio
from CircularProgressBar import CircularProgressBar
from BLE import Connection, communication_manager
from ble_client_test import Debug


# kivy.version('1.9.0')

from BLE import ble_connection
from Speedometer import SpeedMeter



#loop = asyncio.new_event_loop() # Here
#asyncio.set_event_loop(loop) # Here

#ADDRESS, UUID = "78:21:84:9D:37:10", "0000181a-0000-1000-8000-00805f9b34fb"
ADDRESS, UUID = None, None

class MainWindow(Screen): pass

class SecondaryWindow(Screen): pass

class WindowManager(ScreenManager): pass


class Main(MDApp):
    def build(self):
        """setting design for application
        widget development specifications on design.kv"""
        self.theme_cls.theme_style = 'Light'
        self.theme_cls.primary_palette = 'Orange'
        return Builder.load_file(filename='design.kv')

    async def launch_app(self):
        """Asyncronous function for kivy app start"""
        await self.async_run(async_lib='asyncio')

    async def start(self):
        """Asyncronous app making sure start is awaited as coroutine"""
        (done, pending) = await asyncio.wait({self.launch_app()},return_when='FIRST_COMPLETED')

    def on_start(self):
        self.speedmeter = self.root.get_screen('secondary_window').ids.speed
        self.circle_bar = self.root.get_screen('secondary_window').ids.circle_progress
        self.speedmeter.font_size_min = self.speedmeter.font_size

        #self.circle_bar.pos_hint = 0.5, 0.5


    def connect_ble(self, touch: bool) -> None:
        """Function handling BLE connection between App and ESP32"""
        print('in connect_ble')
        Button = self.root.get_screen('main_window').ids.ble_button
        if touch:
            try:
                #asyncio.create_task(run_BLE(self))
                asyncio.create_task(debug_BLE(self))
            except Exception as e:
                print(e)

    def switch_state(self, _, value: bool) -> None:
        """Switch state for adaptive mode switch. When in adaptive mode, the slider is disabled"""
        if value:
            self.root.get_screen('secondary_window').ids.adapt_slider.disabled = True
            self.root.get_screen('secondary_window').ids.adapt_slider.value = self.root.get_screen('secondary_window').ids.adapt_slider.min
        else:
            self.root.get_screen('secondary_window').ids.adapt_slider.disabled = False


    def slider_slide(self, _, value: int) -> None:
        """Sends percentage of assistance wanted to ESP32
        In automatic mode: Use BATTERY and ACCELEROMETER values to determine percentage of use"""
        print(value)
        self.update_speed_value(value)
        self.update_battery_value(value)
        if value == self.root.get_screen('secondary_window').ids.adapt_slider.max:
            self.root.get_screen('secondary_window').ids.adapt_slider.hint_text_color = "red"
        else:
            self.root.get_screen('secondary_window').ids.adapt_slider.hint_text_color = "orange"

    def update_speed_value(self,value: int) -> None:
        """Monitors current speed of bike

        STEPS TO DO:
            +READ FROM BLE TO UPDATE VALUE

        *for debugging purposes it shows the value from slider"""
        if value > 2*self.speedmeter.end_value/3.6:
            pass
        else:
            self.speedmeter.set_value = value - 25
            self.speedmeter.text = f'{value} km/h'
            #self.speedmeter.font_size = self.speedmeter.font_size_min + value

    def update_battery_value(self,value: int) -> None:
        """Monitorss Battery life from bike

        STEPS TO DO:
            +READ FROM BLE TO UPDATE VALUE

        *for debugging purposes it shows the value from slider"""

        self.circle_bar.set_value = value
        self.circle_bar.text = f'{value}%'

async def debug_BLE(app: MDApp) -> None:
    app.root.get_screen('main_window').ids.spinner.active = True
    flag = asyncio.Event()
    try:
        debug = Debug(flag)
        #await debug.connected.wait()
        await debug.flag.wait()
    finally:
        print(f"flag confirmed!")
    for i in range(20):
        print(f"Other coroutine -> {i}")
        await asyncio.sleep(1)
    #app.root.current = 'secondary_window'

async def run_BLE(app: MDApp) -> None:
    """Asyncronous connection protocol for BLE"""
    app.root.get_screen('main_window').ids.spinner.active = True
    print('in run_BLE')
    read_char = "00002A3D-0000-1000-8000-00805f9b34fb"
    write_char = "00002A58-0000-1000-8000-00805f9b34fb"
    flag = asyncio.Event()
    connection = Connection(loop=loop,
                            uuid=UUID,
                            address=ADDRESS,
                            read_char=read_char,
                            write_char=write_char,
                            flag=flag)
    try:
        asyncio.ensure_future(connection.manager())
        asyncio.ensure_future(communication_manager(connection,write_char=write_char,read_char=read_char))
        print(f"fetching connection")
        await connection.flag.wait()
        app.root.current = 'secondary_window'

        #loop.run_forever()
    finally:
        print(f"flag status confirmed!")
        print("Disconnecting...")
        # loop.run_until_complete(connection.cleanup())

if __name__=='__main__':
    async def mainThread():
        """Creating main thread for asyncronous task definition"""
        BikeApp = Main()
        a = asyncio.create_task(BikeApp.start())
        (done,pending) = await asyncio.wait({a}, return_when='FIRST_COMPLETED')

    loop = asyncio.get_event_loop()
    asyncio.run(mainThread())


