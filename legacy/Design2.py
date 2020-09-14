# -*- coding: utf-8 -*-
"""
Created on Tue Sep  8 17:18:22 2020

@author: pierc
"""

from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
import pandas as pd
from pandas.io.json import json_normalize
import numpy as np
import requests
import sqlite3, random, time
import plyer
from kivymd.app import MDApp
from kivy.clock import Clock
import matplotlib
matplotlib.use('module://kivy.garden.matplotlib.backend_kivy')
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvas
import matplotlib.pyplot as plt

KV='''
<GraphLayout>:
    name: "graph"
    
    BoxLayout:
        orientation:'vertical'

BoxLayout:
    orientation:'vertical'

    MDToolbar:
        title: 'MigraineApp'
        md_bg_color: .2, .2, .2, 1
        specific_text_color: 1, 1, 1, 1

    MDBottomNavigation:
        panel_color: .2, .2, .2, 1

        MDBottomNavigationItem:
            name: 'screen 1'
            text: 'Home'
            icon: 'home-analytics'
            
            
            MDLabel:
                text: "How's your head?"
                halign: 'center'    
        
            MDFloatingActionButtonSpeedDial:
                data: app.data
                rotation_root_button: True
                anchor: "right"
                callback: app.callback
                    
                

        MDBottomNavigationItem:
            name: 'screen 2'
            text: 'Analysis'
            icon: 'chart-line'
            on_tab_press : graph.load_graphs()
            
            GraphLayout:
                id: graph
            

        MDBottomNavigationItem:
            name: 'screen 3'
            text: 'Predictors'
            icon: 'weather-cloudy-alert'

            MDLabel:
                text: 'This is where predictions will be made'
                halign: 'center'


'''

class Test(MDApp):
    
    data = {
        'emoticon-cry-outline': 'Migraine',
        'emoticon-frown-outline': 'Persistent',
        'emoticon-sad-outline': 'Building',
        'emoticon-neutral-outline': 'Background',
        'emoticon-happy-outline': 'Pain free'
    }
    
    def build(self):
        #self.theme_cls.primary_palette = "Gray"
        self.theme_cls.theme_style = "Dark"
        self.connect()
        self.create_db()
        self.data_loop()
        
        return Builder.load_string(KV)

    def callback(self, instance):
        value_dict = {
        'emoticon-cry-outline': 5,
        'emoticon-frown-outline': 4,
        'emoticon-sad-outline': 3,
        'emoticon-neutral-outline': 2,
        'emoticon-happy-outline': 1
    }
        icon = instance.icon
        value = value_dict[icon]
        print(value)
        self.store_value(value)
        
    
    def data_callback(self,dt):
        print("data call")
        self.get_data()
        
    def data_loop(self):
        Clock.schedule_interval(self.data_callback, 1800) #use 1800 for every half hour
    
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

    
        
class GraphLayout(BoxLayout):
    
    wid = 0
    def load_graphs(self):
        try:
            """Check if widgets already exist"""
            self.remove_widget(self.wid)
        except:
            print("wid = 0")
        
        self.wid = self.get_fc(1)
        self.add_widget(self.wid)
        #self.add_widget(self.get_fc(2))
        
    def get_fc(self, i):
        pain = Test().return_table_as_df("Pain")
        fig1 = plt.figure()
        fig1.suptitle('Pain Level')
        ax1 = fig1.add_subplot(111)
        pain.plot(x="Time", y="PainScore", kind="line", ax=ax1)
        
        wid = FigureCanvas(fig1)
        #fig1.canvas.mpl_connect('figure_enter_event', enter_figure)
        #fig1.canvas.mpl_connect('figure_leave_event', leave_figure)
        #fig1.canvas.mpl_connect('axes_enter_event', enter_axes)
        #fig1.canvas.mpl_connect('axes_leave_event', leave_axes)
        return wid

   
Test().run()
