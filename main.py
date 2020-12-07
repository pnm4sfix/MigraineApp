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
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

##TODO 
##Save NN model in case app closed
##Add text to prediction page indicating trained status, accuracy and when last trained
##Plot prediction in second graph in analysis tab
##Make home page more interesting
##Blend graph canvas in with background

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
            
        
            MDRoundFlatButton:
                text: "Train"
                pos_hint: {"center_x": .5, "center_y": .5}
                on_press: app.train()
            


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
        #self.prediction_loop()
        self.get_gps()
        self.predict = predict()
        
        
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
        
        historical_df = self.get_two_day_historical()
        
        self.save_to_table(historical_df, "historical")
        
        #db_conn, cursor = self.connect()
        
        #phone_data = self.get_local_properties()
        #weather_data = self.get_weather()
        #data = pd.concat([weather_data, phone_data], axis=1)
        #self.add_db(db_conn, data)
        
        #return daily_forecast_df, hourly_forecast_df
    

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
        time = self.get_datetime(time)
        try:
            db_conn.execute("INSERT INTO Pain(PainScore, Time)"
                            " VALUES (?,?)", (value, time ))
            db_conn.commit()
        except:
            "Couldnt insert new pain score"
        self.get_data()
    
    def predict_pain_state(self, dt):
        """Will use pain NN to predict pain score for the day-
        maybe call once and look at 24 hr predictions for every hour in 
        the day and show plot"""
        print("Pain state loop started")
        daily_forecast_df, hourly_forecast_df = self.get_forecast()
        desc = hourly_forecast_df.description.unique()
        pain_scores = []
        times = []
        df = hourly_forecast_df[["pressure", "temp", "humidity", "wind"]]
        
        for hour in range(24):
            
            df = df.iloc[hour:hour+24,:] # subset first 24 hrs
            time = df.time.iloc[0]
            vector = df.to_numpy().flatten()
            pain_score = self.predict.pain_nn.predict(vector.reshape(1, -1))
            pain_scores.append(pain_score)
            times.append(time)
            
        """Add a prediction plot"""
        self.ids.graph.load_graphs()
        
    
    def prediction_loop(self):
        Clock.schedule_interval(self.predict_pain_state, 10)
    
    def train(self):
        print("Training")
        self.predict.train()
        print("Trained")
        
class GraphLayout(BoxLayout):
    
    wid = 0
    def load_graphs(self):
        try:
            """Check if widgets already exist"""
            self.remove_widget(self.wid)
            self.remove_widget(self.wid2)
        except:
            print("wid = 0")
        
        self.wid = self.pain_plot()
        self.add_widget(self.wid)
        #self.add_widget(self.get_fc(2))
        self.wid2 = self.prediction_plot()
        self.add_widget(self.wid2)
        
    def pain_plot(self):
        pain = Test().return_table_as_df("Pain")
        print(pain.dtypes)
        #plt.style.use('dark_background')
        fig1, ax1 = plt.subplots(facecolor=(.18, .31, .31))
        fig1.suptitle('Pain Level')
        
        
        pain.Time = pd.to_datetime(pain.Time, infer_datetime_format=True)
        #pain.time = pd.to_datetime(pain.Time, infer_datetime_format=True)
        try:
            p = pain.plot(x="Time", y="PainScore", kind="line", ax=ax1)
            ax1.set_facecolor((.36, .61, .62))
            #p.set_axis_bgcolor(0, 0, 0, 50)
        except:
            print("Couldnt print pain data")
        wid = FigureCanvas(fig1)
        return wid
    
    def prediction_plot(self):
        #plt.style.use('dark_background')
        fig1, ax1 = plt.subplots(facecolor=(.18, .31, .31))
        fig1.suptitle('Pain Prediction')
        ax1.set_facecolor((.18, .31, .31))
        wid = FigureCanvas(fig1)
        return wid
        
    def get_fc(self, i):
        pain = Test().return_table_as_df("Pain")
        
        print(pain.dtypes)
        fig1 = plt.figure()
        fig1.suptitle('Pain Level')
        ax1 = fig1.add_subplot(111)
        pain.Time = pd.to_datetime(pain.Time, infer_datetime_format=True)
        #pain.time = pd.to_datetime(pain.Time, infer_datetime_format=True)
        try:
            p = pain.plot(x="Time", y="PainScore", kind="line", ax=ax1)
            
        except:
            print("Couldnt print pain data")
        #fig1.style.use('dark_background')
        wid = FigureCanvas(fig1)
        #fig1.canvas.mpl_connect('figure_enter_event', enter_figure)
        #fig1.canvas.mpl_connect('figure_leave_event', leave_figure)
        #fig1.canvas.mpl_connect('axes_enter_event', enter_axes)
        #fig1.canvas.mpl_connect('axes_leave_event', leave_axes)
        return wid


class predict(object):
    
    def train(self):
        print("Training")
        self.main()
        self.predict_pain()
        self.predict_description()
        
    
    def main(self):
        
        self.db_conn = sqlite3.connect("weather.db")
        self.pain_df = pd.read_sql_query("SELECT * FROM Pain", self.db_conn)
        
        self.weather_df = pd.read_sql_query("SELECT * FROM historical", self.db_conn)
        #elf.pain_df.Time = pd.to_datetime(self.pain_df.Time, format='%Y%m%d%h%m%s', errors='ignore')
        #self.pain_df.Time = self.pain_df.Time.apply(self.test.get_datetime) # wont need this line in final
        self.pain_df.Time = pd.to_datetime(self.pain_df.Time, infer_datetime_format=True)
        
        self.weather_df.time = pd.to_datetime(self.weather_df.time, infer_datetime_format=True)
        self.weather_df.temp = self.weather_df.temp.astype("float64")
        
        self.pain_df["Day1"] = self.pain_df.Time - pd.Timedelta(days=1)
        self.pain_df["Day2"] = self.pain_df.Time - pd.Timedelta(days=2)
    
    
    
    def bootstrap(self, df):
        """Bootstrap pain_df and weather_df to create larger dataset"""
        core_df = pd.DataFrame()
        for n in range(100):
            sample = df.sample(frac = 0.6)
            core_df = pd.concat([core_df, sample], axis=0)
        
        return core_df
    
    
    
    def extract_weather_data(self, pain_df, weather_df):
        """Create 1 day windows of weather data for each pain score -return as a vector?"""
        """Subset weather_df based on time, day1 and day2"""
        vectors = []
        pain_scores = []
        weather_df = weather_df.drop_duplicates("time")
        for n in range(pain_df.shape[0]):
            subset = weather_df.loc[(weather_df.time < pain_df.Time.iloc[n]) & 
                                    (weather_df.time > pain_df.Day1.iloc[n]), 
                                     ["pressure", "temp", "humidity", "wind"]]
            
            vector = subset.to_numpy().flatten()
            pain = pain_df.PainScore.iloc[n]
            vectors.append(vector)
            pain_scores.append(pain)
        
        return vectors, pain_scores
            
        
    def predict_pain(self):                   
        """Bootstrap, get data input and output, normalise, split in to test and train,
        fit with MLP and test"""
        self.boot_pain = self.bootstrap(self.pain_df)  
        self.X, self.Y = self.extract_weather_data(self.boot_pain, self.weather_df)
        #return vectors, pain_scores
        
        X_train, X_test, Y_train, Y_test = train_test_split(self.X, self.Y)
        
        scaler = StandardScaler()
        scaler.fit(X_train)
        X_train = scaler.transform(X_train)
        X_test = scaler.transform(X_test)
        
        self.pain_nn = MLPClassifier(solver='lbfgs', alpha=1e-5,
                     hidden_layer_sizes=(10, 10), random_state=1)
        
        self.pain_nn.fit(X_train, Y_train)
        Y_pred = self.pain_nn.predict(X_test)
        self.pain_accuracy = accuracy_score(Y_test, Y_pred, normalize =True)
        #print("Accuracy is {}".format(accuracy))
        
        
        
              
    
    def predict_description(self):
        """Create net that predicts description"""
        
        self.boot_weather = self.bootstrap(self.weather_df)
        
        self.description = self.boot_weather[["pressure", "temp", "humidity", "wind", "description"]] 
        self.desc_Y = self.description.pop("description")
        self.desc_X = self.description.to_numpy()
        X_train, X_test, Y_train, Y_test = train_test_split(self.desc_X, self.desc_Y)
        
        scaler = StandardScaler()
        scaler.fit(X_train)
        X_train = scaler.transform(X_train)
        X_test = scaler.transform(X_test)
        
        self.desc_nn = MLPClassifier(solver='lbfgs', alpha=1e-5,
                     hidden_layer_sizes=(10, 10), random_state=1,
                     max_iter=400)
        
        self.desc_nn.fit(X_train, Y_train)
        Y_pred = self.desc_nn.predict(X_test)
        self.desc_accuracy = accuracy_score(Y_test, Y_pred, normalize =True)
        #("Accuracy is {}".format(accuracy))

    
    
        
test = Test()   
test.run()
