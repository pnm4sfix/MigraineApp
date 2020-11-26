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
import sqlite3, random
import time as t
import plyer
from kivymd.app import MDApp
from kivy.clock import Clock
import matplotlib
matplotlib.use('module://kivy.garden.matplotlib.backend_kivy')
from kivy.garden.matplotlib.backend_kivyagg import FigureCanvas
import matplotlib.pyplot as plt
import datetime 
from sqlalchemy import create_engine

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
        self.get_gps()
        
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
        self.get_local_properties()
        
    def data_loop(self):
        Clock.schedule_interval(self.data_callback, 1800) #use 1800 for every half hour
    
    def notify_pain_update(self):
        plyer.notification.notify("Pain level", "Enter Pain Level")# figure out how this works
    
    def return_location(self, lat, lon, **kwargs):
        self.lat, self.lon = lat, lon
        
  
    def get_gps(self):
        try:
            plyer.gps.configure(on_location=self.return_location)
            plyer.gps.start(minTime = 5000)
            
            plyer.gps.stop()
        except:
            self.lat = 56.253546
            self.lon = -3.205318
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
        
        self.save_to_table(df, "local")
        
    
    def get_weather(self):
        """look ar rate of change and also do correlation pressure
            for now use leeds but in future app use her GPS"""
        db_conn, cursor=self.connect()
        url="http://api.openweathermap.org/data/2.5/weather?appid=7d3701cfa2460a94e8575feee78ebc4a&q=Leeds"
        json_data=requests.get(url).json()
        json_data=pd.json_normalize(json_data)
        key_vars=["main.pressure", "main.temp", "main.humidity", "wind.speed"]
        json_data=json_data[key_vars]
        api_time=t.time()
        json_data.loc[:,"time"]=api_time
        json_data.columns=["pressure", "temp", "humidity", "wind", "time"]
        print(json_data["pressure"][0])
        return json_data
    
        
    def get_datetime(self, time):
        dt = t.strftime("%b %d %Y %H:%M:%S", t.gmtime(time))     
        return dt
    
    def metadata_loop(self, core_df, data_subset):
        for hour in data_subset:
                time = self.get_datetime(hour["dt"])
                temp = hour["temp"]
                pressure = hour["pressure"]
                humidity = hour["humidity"]
                wind_speed = hour["wind_speed"]
                main_weather = hour["weather"][0]["main"]
                description = hour["weather"][0]["description"]
                
                df = pd.DataFrame([pressure, temp, humidity, wind_speed, 
                                   time, main_weather, description]).transpose()
                df.columns = ["pressure", "temp", "humidity", "wind", "time", 
                              "main_weather", "description"]
                core_df = pd.concat([core_df, df])
        return core_df
    
    def get_two_day_historical(self):
        #lat = 56.253546
        #lon = -3.205318
        lat = self.lat
        lon = self.lon
        """Loop through each hour in last two days"""
        
        hour = 3600
        time = int(t.time())
        t1 = time - (1*(24*3600))
        t2 = time
        times = [t1, t2]
        
        data = {}
        
        for time in times:
            """This number of calls seems to work"""
        
            API_key = "7d3701cfa2460a94e8575feee78ebc4a"
            day5_url = "https://api.openweathermap.org/data/2.5/onecall/timemachine?lat={lat}&lon={lon}&dt={time}&appid={API_key}".format(lat = lat,
                                                                                       lon = lon, 
                                                                                       time = time,
                                                                                       API_key = API_key)
            
            json_data=requests.get(day5_url).json()
            json_data=pd.json_normalize(json_data)
            data[str(time)] = json_data
            
        core_df = pd.DataFrame()
        
        for day in data.keys():
            core_df = self.metadata_loop(core_df, data[day].hourly[0])
        
        return core_df
        
    def get_forecast(self):
        """ Get forecast using API"""
        time = t.time()
        lat = 56.253546
        lon = -3.205318
        API_key = "7d3701cfa2460a94e8575feee78ebc4a"
        forecast_url = "https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&appid={API_key}".format(lat = lat,
                                                                                       lon = lon, 
                                                                                       time = time,
                                                                                       API_key = API_key)
        json_data=requests.get(forecast_url).json()
        json_data=pd.json_normalize(json_data)
        daily_forecast = json_data.daily[0]
        hourly_forecast = json_data.hourly[0]
        
        daily_forecast_df = pd.DataFrame()
        hourly_forecast_df = pd.DataFrame()
        
        daily_forecast_df = self.metadata_loop(daily_forecast_df, daily_forecast)
        hourly_forecast_df = self.metadata_loop(hourly_forecast_df, hourly_forecast)
        
        return daily_forecast_df, hourly_forecast_df
    
    def save_to_table(self, df, table_name):
        """Takes pandas df and creates or appends to a sql table"""
        engine = create_engine('sqlite:///weather.db', echo=True)
        sqlite_connection = engine.connect()
        sqlite_table = table_name
        df.to_sql(sqlite_table, sqlite_connection, if_exists='append')
        sqlite_connection.close()
    
    def connect(self):
            db_conn = sqlite3.connect('weather.db')
            theCursor = db_conn.cursor()
            return db_conn, theCursor
    
    
    def get_data(self):
        """OLD -Get weather data and local phone data and add to db.
        NEW - Get weather data for last 2 days and add to db with sqlalchemy."""
        daily_forecast_df, hourly_forecast_df = self.get_forecast()
        historical_df = self.get_two_day_historical()
        
        self.save_to_table(historical_df, "historical")
        
        #db_conn, cursor = self.connect()
        
        #phone_data = self.get_local_properties()
        #weather_data = self.get_weather()
        #data = pd.concat([weather_data, phone_data], axis=1)
        #self.add_db(db_conn, data)
        
        return daily_forecast_df, hourly_forecast_df
    

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
        """db_conn.execute(
            "CREATE TABLE if not exists Weather(ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"
            " Pressure INT NOT NULL , Temp INT NOT NULL, Humidity INT NOT NULL, Wind INT NOT NULL," 
            "Time INT NOT NULL, locPress INT, locHum INT, locTemp INT);")
        db_conn.commit()"""
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
        time=int(t.time())
        try:
            db_conn.execute("INSERT INTO Pain(PainScore, Time)"
                            " VALUES (?,?)", (value, time ))
            db_conn.commit()
        except:
            "Couldnt insert new pain score"
        self.get_data()

    
        
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
        print(pain.dtypes)
        fig1 = plt.figure()
        fig1.suptitle('Pain Level')
        ax1 = fig1.add_subplot(111)
        pain.Time = pd.to_datetime(pain.Time)
        try:
            pain.plot(x="Time", y="PainScore", kind="line", ax=ax1)
        except:
            print("Couldnt print pain data")
        wid = FigureCanvas(fig1)
        #fig1.canvas.mpl_connect('figure_enter_event', enter_figure)
        #fig1.canvas.mpl_connect('figure_leave_event', leave_figure)
        #fig1.canvas.mpl_connect('axes_enter_event', enter_axes)
        #fig1.canvas.mpl_connect('axes_leave_event', leave_axes)
        return wid

   
Test().run()
