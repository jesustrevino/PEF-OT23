from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.uix.screenmanager import ScreenManager
from kivy.lang import Builder
import kivy

#kivy.version('1.9.0')

from BLE import ble_connection
import asyncio

ADDRESS, UUID = "", ""

class UI(ScreenManager):
    pass

class Main(MDApp):
    def build(self):
        # setting design for application
        self.theme_cls.theme_style = 'Light'
        self.theme_cls.primary_palette = 'Orange'
        self.theme_cls.theme_style_switch_animation = ''

        # widget development specifications on design.kv
        Builder.load_file(filename='design.kv')
        """screen = MDScreen()
        btn = MDRectangleFlatButton(text="Hello World",
                                    pos_hint={'center_x': 0.5, 'center_y': 0.5}
                                    )
        screen.add_widget(btn)"""
        return UI()

    def change_mode(self, checked, value) -> None:
        """Function handling adaptive mode on bike"""
        if value:
            self.theme_cls.theme_style = 'Light'
        else:
            self.theme_cls.theme_style = 'Dark'

    def ble_connect(self, touch: bool) -> None:
        """Function handling adaptive mode on bike"""
        if touch:
            asyncio.run(ble_connection(ADDRESS,UUID))
            self.theme_cls.theme_style = 'Dark'



def run_app():
    Main().run()
    #asyncio.run(ble_connection(ADDRESS, UUID))

if __name__=='__main__':
    run_app()

