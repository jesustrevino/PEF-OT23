from kivymd.app import MDApp
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
import asyncio
from CircularProgressBar import CircularProgressBar
from CustomSpeed import Speedometer


#kivy.version('1.9.0')

from BLE import ble_connection
from Speedometer import SpeedMeter



loop = asyncio.new_event_loop() # Here
asyncio.set_event_loop(loop) # Here

ADDRESS, UUID = "", "4295124f-50e1-4d13-bf04-c5dea961600b"

class MainWindow(Screen): pass

class SecondaryWindow(Screen): pass

class WindowManager(ScreenManager): pass


class Main(MDApp):
    def build(self):
        # setting design for application
        # widget development specifications on design.kv
        self.theme_cls.theme_style = 'Light'
        self.theme_cls.primary_palette = 'Orange'
        return Builder.load_file(filename='design.kv')

    def on_start(self):
        self.speedmeter = self.root.get_screen('secondary_window').ids.speed
        self.circle_bar = self.root.get_screen('secondary_window').ids.circle_progress
        self.speedmeter.font_size_min = self.speedmeter.font_size

        #self.circle_bar.pos_hint = 0.5, 0.5


    def connect_ble(self, touch: bool) -> None:
        """Function handling BLE connection between App and ESP32"""
        Button = self.root.get_screen('main_window').ids.ble_button
        if touch:
            try:
                #asyncio.ensure_future(ble_connection(ADDRESS,UUID))
                #loop.run_forever()
                loop.run_until_complete(ble_connection(ADDRESS,UUID))
            finally:
                print("Closing Loop")
                loop.close()
            print('in connect_ble')

    def switch_state(self, _, value: bool) -> None:
        """Switch state for adaptive mode switch. When in adaptive mode, the slider is disabled"""
        if value:
            self.root.get_screen('secondary_window').ids.adapt_slider.disabled = True
            self.root.get_screen('secondary_window').ids.adapt_slider.value = self.root.get_screen('secondary_window').ids.adapt_slider.min
        else:
            self.root.get_screen('secondary_window').ids.adapt_slider.disabled = False


    def slider_slide(self, _, value: int) -> None:
        """Sends percentage of assistance wanted to ESP32"""
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
        if value > 2*self.speedmeter.end_value/(3.6):
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




def run_app():
    Main().run()
    #asyncio.run(ble_connection(ADDRESS, UUID))

if __name__=='__main__':
    run_app()

