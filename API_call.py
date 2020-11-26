# -*- coding: utf-8 -*-
"""
Created on Sun Nov 15 18:50:22 2020

@author: pierc
"""
import pandas as pd
import time as t
import requests
import numpy as np
import sqlite3
from sqlalchemy import create_engine

def get_datetime(time):
    datetime = t.strftime("%b %d %Y %H:%M:%S", t.gmtime(time))     
    return datetime

def metadata_loop(core_df, data_subset):
    for hour in data_subset:
            time = get_datetime(hour["dt"])
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

def get_two_day_historical():
    lat = 56.253546
    lon = -3.205318
    
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
        core_df = metadata_loop(core_df, data[day].hourly[0])
    
    return core_df
    
def get_forecast():
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
    
    daily_forecast_df = metadata_loop(daily_forecast_df, daily_forecast)
    hourly_forecast_df = metadata_loop(hourly_forecast_df, hourly_forecast)
    
    return daily_forecast_df, hourly_forecast_df

def save_to_table(df, table_name):
    """Takes pandas df and creates or appends to a sql table"""
    engine = create_engine('sqlite:///test.db', echo=True)
    sqlite_connection = engine.connect()
    sqlite_table = table_name
    df.to_sql(sqlite_table, sqlite_connection, if_exists='append')
    sqlite_connection.close()

def connect():
        db_conn = sqlite3.connect('test.db')
        theCursor = db_conn.cursor()
        return db_conn, theCursor

def return_table_as_df(table):
        """Generic function to return a db table as df"""
        db_conn, cursor = connect()
        df = pd.read_sql_query("SELECT * FROM " +table, db_conn)
        return df
    

    
    
        
    
      
    


