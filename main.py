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
from acchelper import AccHelper
from gyrohelper import GyroHelper


# ADDRESS, UUID = "78:21:84:9D:37:10", "0000181a-0000-1000-8000-00805f9b34fb"
ADDRESS, UUID = None, None
GPS_ON = True
DEBUG_GPS = False

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
    acc_q = asyncio.Queue()
    man_q = asyncio.Queue()

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
        self.manip_button = self.root.get_screen('secondary_window').ids.manip_button
        self.speedmeter.font_size_min = self.speedmeter.font_size
        self.sp_button = self.root.get_screen('secondary_window').ids.sp_button
        self.read_slider_text = self.root.get_screen('secondary_window').ids.read_slider_text
        self.test_button = self.root.get_screen('secondary_window').ids.test_button
        
        self.circle_bar.text = f'0%'
        self.read_slider_text.text = f'0 %'
        self.manip_button.text = f'M: x'
        
        self.per_button_pressed = True
        self.km_button_pressed = False
        self.angle_button_pressed = False
        
        self.set_angle = 0
        self.slider_label = 'slider'
        self.slider_value = 0
        self.slider_flag = False
        self.test_counter = 0
        
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
                if DEBUG_GPS:
                	self.root.current = 'secondary_window'
                else:
                	asyncio.create_task(run_BLE(self, self.send_q, self.battery_q, self.drop_q, self.angle_q, self.man_q))
                GpsHelper().run(self.speed_q)
                asyncio.ensure_future(self.update_battery_value())
                asyncio.ensure_future(self.update_speed_value())
                asyncio.ensure_future(self.update_angle_value())
                asyncio.ensure_future(self.update_manipulation_value())
                
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
            self.root.get_screen('secondary_window').ids.adapt_slider.disabled = False
            self.send_q.put_nowait(json.dumps({'adapt': 1}))
            self.root.get_screen('secondary_window').ids.adapt_slider.value = self.root.get_screen(
                'secondary_window').ids.adapt_slider.min
        else:
            # self.root.get_screen('secondary_window').ids.adapt_slider.disabled = False
            self.root.get_screen('secondary_window').ids.adapt_slider.disabled = False
            self.send_q.put_nowait(json.dumps({'adapt': 0}))

    def slider_on_value(self, _, value: int) -> None:
        """Sends percentage of assistance wanted to ESP32
        In automatic mode: Use BATTERY and ACCELEROMETER values to determine percentage of use"""
        # print(value)
        label = 'slider'
        if self.per_button_pressed:
            self.read_slider_text.text = f'{value} %'
            value = int(180 * value / 100)
            label = 'slider_per'
        if self.km_button_pressed:
            value = value
            label = 'slider_km'
        self.slider_label = label
        self.slider_value = value
        if label == 'slider_km':
            self.sp_button.text = f'SP: {value}'
            self.read_slider_text.text = f'{value} km/h'
            
            
        if value == self.root.get_screen('secondary_window').ids.adapt_slider.max:
            self.root.get_screen('secondary_window').ids.adapt_slider.hint_text_color = "red"
            if not self.slider_flag:
            	self.send_q.put_nowait(json.dumps({self.slider_label: self.slider_value}))
            	self.slider_flag = True
        elif value == self.root.get_screen('secondary_window').ids.adapt_slider.min and not self.slider_flag:
            self.send_q.put_nowait(json.dumps({self.slider_label: self.slider_value}))
            self.slider_flag = True
        else:
            self.root.get_screen('secondary_window').ids.adapt_slider.hint_text_color = "orange"
            self.slider_flag = False
            
    def slider_touch_up(self, *args) -> None:
        try:
            self.send_q.put_nowait(json.dumps({self.slider_label: self.slider_value}))
        except asyncio.QueueFull:
            pass
            
    		
    def slider_unit_km(self, touch: bool) -> None:
        if touch:
            self.km_button_pressed = True
            self.per_button_pressed = False
            self.read_slider_text.text = f'0 km/h'
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
            self.read_slider_text.text = f'0 %'
            self.root.get_screen('secondary_window').ids.adapt_slider.value = 0
            self.root.get_screen('secondary_window').ids.adapt_slider.max = 100
            self.root.get_screen('secondary_window').ids.adapt_slider.step = 5
            self.root.get_screen('secondary_window').ids.adapt_slider.color = "orange"
            self.root.get_screen('secondary_window').ids.adapt_slider.thumb_color_inactive = "orange"
            self.root.get_screen('secondary_window').ids.adapt_slider.thumb_color_active = "orange"
    
    def send_angle(self, touch: bool) -> None:
        print('in_touch_angle')
        if touch:
            try:
            	self.send_q.put_nowait(json.dumps({'set_angle': int(self.set_angle)}))
            	print(f'set_angle : {self.set_angle}')
            	# self._pressed = True
            except Exception as e:
            	print(f'EXCEPTION IN ANGLE : {e}')
            	
    def test_button_press(self, touch: bool) -> None:
        if touch:
            self.test_counter += 1
            self.test_button.text = f'test: {self.test_counter}'           	
            
    
    async def update_angle_value(self) -> None:
    	while True:
    	   print('in_angle')
    	   try:
    	   	set_angle = await self.angle_q.get()
    	   	set_angle = float(set_angle)
    	   	print(f'angle -> {set_angle}')
    	   	self.an_button.text = f'Angle : {set_angle}°'
    	   except Exception as e:
    	   	print(f'EXCEPTION IN ANGLE : {e}')
    	   	await asyncio.sleep(1.0)
    	   print(f'angle displayed: {set_angle}')
    	   self.set_angle = set_angle

    async def update_manipulation_value(self) -> None:
        """FOR DEBUGGING PURPOSES"""
        while True:
            print('in_manipulation')
            try:
                manip = await self.man_q.get()
                manip = int(manip)
                self.manip_button.text = f'M: {manip}' #TODO: convert to percentage
            except Exception as e:
                print(f'EXCEPTION IN MANIP: {e}')
                await asyncio.sleep(1.0)
            
    async def update_speed_value(self) -> None:
        """Monitors current speed of bike"""
        speed = 0
        while True:
            print("in_speed")
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
            print("in_battery")
            try:
                current_battery_life = await self.battery_q.get()
                battery_life = float(current_battery_life)
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
            


async def run_BLE(app: MDApp, send_q: asyncio.Queue, battery_q: asyncio.Queue, drop_q: asyncio.Queue, angle_q: asyncio.Queue, man_q: asyncio.Queue) -> None:
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
                                                    battery_q=battery_q, angle_q=angle_q,
                                                    man_q=man_q))
        print(f"fetching connection")
        await connection.flag.wait()
    finally:
        print(f"flag status confirmed!")
        AccHelper().run(send_q)
        
        
        
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
