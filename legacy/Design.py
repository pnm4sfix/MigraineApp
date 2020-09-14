from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty
import pandas as pd
from pandas.io.json import json_normalize
import numpy as np
import requests
import sqlite3, random, time
import plyer
from kivymd.app import MDApp
from kivy.clock import Clock
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvasKivyAgg


"""Use emoticons"""

KV = '''
<ContentNavigationDrawer>:

    ScrollView:

        MDList:

            OneLineListItem:
                text: "Home"
                on_press:
                    root.nav_drawer.set_state("close")
                    root.screen_manager.current = "scr 1"

            OneLineListItem:
                text: "Analysis"
                on_press:
                    root.nav_drawer.set_state("close")
                    root.screen_manager.current = "scr 2"


Screen:

    MDToolbar:
        id: toolbar
        pos_hint: {"top": 1}
        elevation: 10
        title: "Menu"
        left_action_items: [["menu", lambda x: nav_drawer.set_state("open")]]
        md_bg_color: app.theme_cls.primary_dark

    NavigationLayout:
        x: toolbar.height

        ScreenManager:
            id: screen_manager

            Screen:
                name: "scr 1"
                
                MDRoundFlatButton:
                    text: "Migraine"
                    font_size: "20sp"
                    pos_hint: {"center_x": .5, "center_y": .8}
                    on_press : app.store_value(5)
                
                MDRoundFlatButton:
                    text: "Persistent"
                    font_size: "20sp"
                    pos_hint: {"center_x": .5, "center_y": .65}
                    on_press : app.store_value(4)
                
                MDRoundFlatButton:
                    text: "Building"
                    font_size: "20sp"
                    pos_hint: {"center_x": .5, "center_y": .5}
                    on_press : app.store_value(3)
                    
                MDRoundFlatButton:
                    text: "Background"
                    font_size: "20sp"
                    pos_hint: {"center_x": .5, "center_y": .35}
                    on_press : app.store_value(2)
                    
                MDRoundFlatButton:
                    text: "Pain free"
                    font_size: "20sp"
                    pos_hint: {"center_x": .5, "center_y": .2}
                    on_press : app.store_value(1)
                    
                

            Screen:
                name: "scr 2"

                MDLabel:
                    text: "Screen 2"
                    halign: "center"

        MDNavigationDrawer:
            id: nav_drawer

            ContentNavigationDrawer:
                screen_manager: screen_manager
                nav_drawer: nav_drawer
'''


class ContentNavigationDrawer(BoxLayout):
    screen_manager = ObjectProperty()
    nav_drawer = ObjectProperty()
    


class MigraineApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        #self.theme_cls.accent_color = "Blue"
        self.connect()
        self.create_db()
        self.data_loop()
        return Builder.load_string(KV)
    
    def callback(self,dt):
        print("data call")
        self.get_data()
        
    def data_loop(self):
        Clock.schedule_interval(self.callback, 30) #use 1800 for every half hour
    
    def notify_pain_update(self):
        plyer.notification.notify("Pain level", "Enter Pain Level")# figure out how this works
    
    def get_gps(self):
        try:
            plyer.gps.start(1000, 1)
        except:
            print("Couldnt get gps")
        
    def get_local_properties(self):
        try:
            pressure=plyer.barometer.pressure
        except:
            print("Couldnt get pressure")
            pressure = np.nan
        try:
            humidity=plyer.humidity.tell
        except:
            print("Couldnt get humidity")
            humidity = np.nan
        try:
            temperature=plyer.temperature.temperature
        except:
            temperature = np.nan
            print("Couldnt get temperature")
        df = pd.DataFrame([pressure, humidity, temperature]).transpose()
        df.columns = ["locPress", "locHum", "locTemp"]   
        return df
    
    def get_weather(self):
        """look ar rate of change and also do correlation pressure
            for now use leeds but in future app use her GPS"""
        db_conn, cursor=self.connect()
        url="http://api.openweathermap.org/data/2.5/weather?appid=7d3701cfa2460a94e8575feee78ebc4a&q=Leeds"
        json_data=requests.get(url).json()
        json_data=pd.json_normalize(json_data)
        key_vars=["main.pressure", "main.temp", "main.humidity", "wind.speed"]
        json_data=json_data[key_vars]
        api_time=time.time()
        json_data.loc[:,"time"]=api_time
        json_data.columns=["pressure", "temp", "humidity", "wind", "time"]
        print(json_data["pressure"][0])
        return json_data
    
    def get_data(self):
        """Get weather data and local phone data and add to db"""
        db_conn, cursor = self.connect()
        phone_data = self.get_local_properties()
        weather_data = self.get_weather()
        data = pd.concat([weather_data, phone_data], axis=1)
        self.add_db(db_conn, data)


    def connect(self):
        db_conn = sqlite3.connect('weather.db')
        theCursor = db_conn.cursor()
        return db_conn, theCursor
    

    def drop_tables(self):
        db_conn, cursor = self.connect()
        try:
            db_conn.execute("DROP TABLE Weather")
        except:
            print("no weather table")
        try:
            db_conn.execute("DROP TABLE Pain")
            db_conn.commit()
        except:
            print("no pain table")


    def create_db(self):
        db_conn, cursor=self.connect()
        #
        db_conn.execute(
            "CREATE TABLE if not exists Weather(ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"
            " Pressure INT NOT NULL , Temp INT NOT NULL, Humidity INT NOT NULL, Wind INT NOT NULL," 
            "Time INT NOT NULL, locPress INT, locHum INT, locTemp INT);")
        db_conn.commit()
        #
        db_conn.execute(
            "CREATE TABLE if not exists Pain(ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"
            " PainScore INT NOT NULL, Time INT NOT NULL);")
        db_conn.commit()
        

    def add_db(self, db_conn, df):
        try:
            
            db_conn.execute(
                "INSERT INTO Weather(Pressure, Temp, Humidity, Wind, Time, "
                "locPress, locHum, locTemp) " +
                "VALUES (?,?,?,?,?,?,?,?)", (np.float(df["pressure"][0]), df["temp"][0],
                                       np.float(df["humidity"][0]), df["wind"][0], df["time"][0],
                                       df["locPress"][0], df["locHum"][0], df["locTemp"][0]))
            db_conn.commit()
        except:
            print("Couldnt insert values")
            
    def return_table_as_df(self, table):
        """Generic function to return a db table as df"""
        db_conn, cursor = self.connect()
        df = pd.read_sql_query("SELECT * FROM " +table, db_conn)
        return df
    

    def store_value(self, value):
        db_conn, theCursor = self.connect()
        t=time.time()
        try:
            db_conn.execute("INSERT INTO Pain(PainScore, Time)"
                            " VALUES (?,?)", (value, t ))
            db_conn.commit()
        except:
            "Couldnt insert new pain score"
    


MigraineApp().run()