import pandas as pd
from pandas.io.json import json_normalize
import numpy as np
import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.pagelayout import PageLayout
from kivy.properties import ObjectProperty
#from kivy.uix.listview import ListItemButton
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.core.audio import SoundLoader
import sqlite3, random, time
from sklearn import linear_model
import plyer
from kivy.lang import Builder

#to do-work on test function, create fake dataset to practice classiication

#collect dataset
#classify dataset(probably have to use data from 48 hours before for prediction)
#use last 24hrs to correlate acute triggers

Builder.load_string ('''
<Weather>:
    
        
        BoxLayout:
                orientation:"vertical"
                Button:
                        text:"Migraine"
                        on_press: root.store_value(4)
                Button:
                        text:"Persistent"
                Button:
                        text:"Building"
                Button:
                        text:"Background"
                Button:
                        text:"Pain Free"     
            
        BoxLayout:
                orientation:"vertical"
                Button:
                        text:"Migraine"
                Button:
                        text:"Persistent"
                Button:
                        text:"Building"
                Button:
                        text:"Background"
                Button:
                        text:"Pain Free"
''')

##to do-figure out how to extract info from retrieved corr table
        #test

class Weather(PageLayout):
    
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
    
    def analysis(self):
        """Analyses data from past 12 hours
        this is main function: triggers analysis of past 12 hours-looking for single values that describe past trend
        pain value, time, and aggregate measures are inserted into a correlation table, when there is enough data,
        a proper correlation can be achieved-another function is required to look at weather forecasts and past 12 hr data
        and produce warnings based on events highly correlated with migraine onset"""
        #maybe i can condense it to mean, and the standard deviation-from which i can estimate max and min
        db_conn, cursor=self.connect()
        df=pd.read_sql_query("SELECT * FROM Weather", db_conn)
        #print(np.array(df.Time)[-1])
        last_entry = np.array(df.Time)[-1]
        window_12hrs = 60*60*12 #secs*mins*12hrs
        window_start = last_entry-window_12hrs
        window=df[df.Time > window_start]
        #perform calculations, mean, variance (SD) and slope(linear_regression) using aggregate function of pandas
        means = window.aggregate(np.mean)
        stds = window.aggregate(np.std)
        highs = window.aggregate(np.max)
        lows = window.aggregate(np.min)

        #linear_regression for here-use multiple linear regression for correlation analysis
        #reg=linear_model.LinearRegression() ##try pd.ols for this-cleaner in pandas
        #reg.fit(window, np.arange(window.shape[0]))
        #slopes=reg.coef_

        analysis_df=pd.concat([means, stds, highs, lows], axis=1)
        analysis_df.columns=["means", "stds", "highs", "lows"]
        analysis_df["slopes"]=slopes
        analysis_df=analysis_df.T
        return analysis_df

    def test_db(self, db_conn, cursor):
        results=cursor.execute("SELECT Pressure from Weather")
        for result in results:
            print(result)
        df=pd.read_sql_query("SELECT * FROM Weather", db_conn)
        print(df)
        df = pd.read_sql_query("SELECT * FROM Corr", db_conn)
        new_df=self.recover_corr_df(df)
        df=pd.concat([df.PainScore, new_df], axis=1)
        return(df)
        #print(df["Pressure":"Wind"].aggregate(self.retrieval))
    """
    weather=get_weather()
    print(weather)
    db_conn, theCursor=create_db()
    print(db_conn)
    add_db(db_conn, weather)
    test_db(db_conn, theCursor)"""

class WeatherApp(App):
    def build(self):
        Weather().connect()#Weather().connect()
        #Weather().drop_tables()
        Weather().create_db()#Weather().create_db()
        Weather().data_loop()#Weather().data_loop()
        return Weather()
    

#dbApp = Weather()#WeatherApp()
#dbApp.run()
        
if __name__ == '__main__':
    WeatherApp().run()    