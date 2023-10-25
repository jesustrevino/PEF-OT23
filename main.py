from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.utils import platform
import asyncio
import json

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
    send_q = asyncio.Queue()
    speed_q = asyncio.Queue()
    drop_q = asyncio.Queue()
    battery_q = asyncio.Queue()
    angle_q = asyncio.Queue()

    def build(self):
        """setting design for application widget development specifications on design.kv"""
        self.theme_cls.theme_style = 'Dark'
        self.theme_cls.primary_palette = 'Orange'
        # GPS setup and start
        if GPS_ON:
            self.get_permissions()
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
        self.an_button = self.root.get_screen('secondary_window').ids.angle_button
        self.speedmeter.font_size_min = self.speedmeter.font_size
        
        self.circle_bar.text = f'0%'
        
        self.per_button_pressed = True
        self.km_button_pressed = False
        self.angle_button_pressed = None
        
        self.set_angle = 0
        
    def get_permissions(self):
    	# Request permissions on Android
        if platform == 'android':
            from android.permissions import Permission, request_permissions
            def callback(permission, results):
                if all([res for res in results]):
                    print('Got all permissions')
                else:
                    print('Did not get all permissions')

            try:
                request_permissions([Permission.ACCESS_COARSE_LOCATION, Permission.ACCESS_FINE_LOCATION, Permission.BLUETOOTH, Permission.BLUETOOTH_ADMIN, Permission.WAKE_LOCK, Permission.BLUETOOTH_CONNECT, Permission.ACCESS_BACKGROUND_LOCATION,
                callback])
            except Exception as e:
                print(e)

    def connect_ble(self, touch: bool) -> None:
        """Function handling BLE connection between App and ESP32"""
        if touch:
            try:
                asyncio.create_task(run_BLE(self, self.send_q, self.battery_q, self.drop_q, self.angle_q))
                GpsHelper().run(self.speed_q)
                asyncio.ensure_future(self.update_battery_value())
                asyncio.ensure_future(self.update_speed_value())
                asyncio.ensure_future(self.update_angle_value())
                
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
            self.send_q.put_nowait(json.dumps({'adapt': 1}))
            self.root.get_screen('secondary_window').ids.adapt_slider.value = self.root.get_screen(
                'secondary_window').ids.adapt_slider.min
        else:
            self.root.get_screen('secondary_window').ids.adapt_slider.disabled = False
            self.send_q.put_nowait(json.dumps({'adapt': 0}))

    def slider_slide(self, _, value: int) -> None:
        """Sends percentage of assistance wanted to ESP32
        In automatic mode: Use BATTERY and ACCELEROMETER values to determine percentage of use"""
        # print(value)
        label = 'slider'
        if self.per_button_pressed:
            value = int(180 * value / 100)
            label = 'slider_per'
        if self.km_button_pressed:
            value = value
            label = 'slider_km'
        try:
            self.send_q.put_nowait(json.dumps({label: value}))
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
            self.root.get_screen('secondary_window').ids.adapt_slider.max = 40
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
            try:
            	self.send_q.put_nowait(json.dumps({'set_angle', self.set_angle}))
            	print(f'set_angle : {self.set_angle}')
            	# self.angle_button_pressed = True
            except Exception as e:
            	pass
            
    
    async def update_angle_value(self) -> None:
    	while True:
    	   print('in angle')
    	   try:
    	   	set_angle = await self.angle_q.get()
    	   	set_angle = float(set_angle)
    	   	print(f'angle -> {set_angle}')
    	   	self.an_button.text = f'Angle : {set_angle}°' 
    	   except Exception as e:
    	   	print(f'EXCEPTION IN ANGLE : {e}')
    	   	set_angle = 0
    	   	await asyncio.sleep(1.0)
    	   print(f'angle displayed: {set_angle}')
    	   self.set_angle = set_angle
    	   
    	   if self.angle_button_pressed:
    	   	break

    async def update_speed_value(self) -> None:
        """Monitors current speed of bike"""
        speed = 0
        while True:
            print("in speed")
            try:
                speed = await self.speed_q.get()
                speed = float(speed)
                print(f"speed-> {speed}")
                await self.send_q.put(json.dumps({'speed': speed}))
            except Exception as e:
                print(f'Exception in speed:: {e}')
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
        battery_life = 0
        while True:
            print("in battery")
            try:
                current_battery_life = float(await self.battery_q.get())
                battery_life = current_battery_life
                battery_life = int(battery_life)
                print(f"battery-> {battery_life}")
                if battery_life > 100:
                    battery_life = int(100)
                elif battery_life < 0:
            	    battery_life = 0
                else:
                    self.circle_bar.set_value = battery_life
                    self.circle_bar.text = f'{battery_life}%'
            except Exception as e:
                print(f'Exception in battery:: {e}')
                await asyncio.sleep(2.0)
            


async def run_BLE(app: MDApp, send_q: asyncio.Queue, battery_q: asyncio.Queue, drop_q: asyncio.Queue, angle_q: asyncio.Queue) -> None:
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
                                                    send_q=send_q,
                                                    battery_q=battery_q, angle_q=angle_q))
        print(f"fetching connection")
        await connection.flag.wait()
    finally:
        print(f"flag status confirmed!")
        
    try: 
        app.root.current = 'secondary_window'
    except Exception as e:
    	print(f'EXCEPTION WHEN CHANGING WINDOW -> {e}')


if __name__ == '__main__':
    async def mainThread():
        """Creating main thread for asynchronous task definition"""
        BikeApp = Main()
        a = asyncio.create_task(BikeApp.start())
        (done, pending) = await asyncio.wait({a}, return_when='FIRST_COMPLETED')


    loop = asyncio.get_event_loop()
    asyncio.run(mainThread())
