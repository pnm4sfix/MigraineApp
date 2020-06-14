import pandas as pd
from pandas.io.json import json_normalize
import numpy as np
import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.pagelayout import PageLayout
from kivy.properties import ObjectProperty
from kivy.uix.listview import ListItemButton
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
    #db_conn = sqlite3.connect('weather.db')

    def callback(self,dt):
        self.get_weather()
    def data_loop(self):
        Clock.schedule_interval(self.callback, 1800) #use 1800 for every half hour
    
    def notify_pain_update():
        plyer.notification.notify("Pain level", "Enter Pain Level")# figure out how this works
    
    def get_gps():
        plyer.gps.start(1000, 1)
        
    def get_local_properties():
        pressure=plyer.barometer.pressure
        humidity=plyer.humidity.tell
        temperature=plyer.temperature.temperature
        
    #look ar rate of change and also do correlation pressure
    #for now use leeds but in future app use her GPS
    def get_weather(self):
        db_conn, cursor=self.connect()
        url="http://api.openweathermap.org/data/2.5/weather?appid=7d3701cfa2460a94e8575feee78ebc4a&q=Leeds"
        print(url)
        json_data=requests.get(url).json()
        print(json_data)
        json_data=json_normalize(json_data)
        print(json_data)
        key_vars=["main.pressure", "main.temp", "main.humidity", "wind.speed"]
        json_data=json_data[key_vars]
        api_time=time.time()
        json_data["time"]=api_time
        json_data.columns=["pressure", "temp", "humidity", "wind", "time"]
        print(json_data["pressure"][0])
        #call add db function
        self.add_db(db_conn, json_data)
        #need function to check timeframe of dataframe-if exceeds 12 hours delete old rows-or not could just archive data

    def analysis(self):
        """Analyses data from past 12 hours"""
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
        reg=linear_model.LinearRegression() ##try pd.ols for this-cleaner in pandas
        reg.fit(window, np.arange(window.shape[0]))
        slopes=reg.coef_

        analysis_df=pd.concat([means, stds, highs, lows], axis=1)
        analysis_df.columns=["means", "stds", "highs", "lows"]
        analysis_df["slopes"]=slopes
        analysis_df=analysis_df.T
        return analysis_df


    def connect(self):
        db_conn = sqlite3.connect('weather.db')
        theCursor = db_conn.cursor()
        return db_conn, theCursor
    #make pd dataframe and add to sqlite db


    def drop_tables(self):
        db_conn, cursor = self.connect()
        try:
            db_conn.execute("DROP TABLE Weather")
        except:
            print("no weather table")
        try:
            db_conn.execute("DROP TABLE Corr")
            db_conn.commit()
        except:
            print("no corr table")


    def create_db(self):
        db_conn, cursor=self.connect()
        #
        db_conn.execute(
            "CREATE TABLE if not exists Weather(ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"
            " Pressure INT NOT NULL , Temp INT NOT NULL, Humidity INT NOT NULL, Wind INT NOT NULL, Time INT NOT NULL);" )
        db_conn.commit()
        #
        db_conn.execute(
            "CREATE TABLE if not exists Corr(ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,"
            " PainScore INT NOT NULL, Time INT NOT NULL, Pressure INT NOT NULL , Temp INT NOT NULL, Humidity INT NOT NULL, "
            "Wind INT NOT NULL);")
        db_conn.commit()


    def retrieval(self, array):
        return np.frombuffer(array, dtype="float64")
    
    def recover_corr_df(self, df):
        #subset the pressure, wind, humidity, temp data
        subset=df[df.columns[-4:]]
        recovered_df=subset.applymap(self.retrieval)
        return(recovered_df)
    
    def correlation(self):
        #retrieve all data from sql table
        pass
    def add_db(self, db_conn, DF):

            print(DF["pressure"])
            print(DF["pressure"][0])
            pressure=np.float(DF["pressure"][0])
            humidity=np.float(DF["humidity"][0])
            db_conn.execute(
                "INSERT INTO Weather(Pressure, Temp, Humidity, Wind, Time) " +
                "VALUES (?,?,?,?,?)", (pressure, DF["temp"][0], humidity, DF["wind"][0], DF["time"][0]))
            db_conn.commit()

            print("Couldnt insert values")

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

    def store_value(self, value):
        """this is main function: triggers analysis of past 12 hours-looking for single values that describe past trend
        pain value, time, and aggregate measures are inserted into a correlation table, when there is enough data,
        a proper correlation can be achieved-another function is required to look at weather forecasts and past 12 hr data
        and produce warnings based on events highly correlated with migraine onset"""
        db_conn, theCursor = self.connect()
        self.test_db(db_conn, theCursor)
        df = self.analysis()
        t=time.time()
        #not sure why asbytes
        db_conn.execute("INSERT INTO Corr(PainScore, Time, Pressure, Temp, Humidity, Wind)"
                        " VALUES (?,?,?,?,?,?)", (value, t, self.asbytes(df.Pressure), self.asbytes(df.Temp),
                                                  self.asbytes(df.Humidity), self.asbytes(df.Wind)))
        db_conn.commit()
        
    def asbytes(self, pdseries):
        return np.array(pdseries).tobytes()

    def get_gps(self):
        pass

    def get_local_pressure(self):
        pass

    def get_local_temp(self):
        pass



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