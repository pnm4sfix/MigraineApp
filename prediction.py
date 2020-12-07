# -*- coding: utf-8 -*-
"""
Created on Sat Dec  5 21:20:59 2020

@author: pierc
"""

import pandas as pd
import sqlite3, main
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

class predict(object):
    
    def main(self):
        self.test = main.Test()
        self.db_conn = sqlite3.connect("App//dist//main//weather.db")
        self.pain_df = pd.read_sql_query("SELECT * FROM Pain", self.db_conn)
        
        self.weather_df = pd.read_sql_query("SELECT * FROM historical", self.db_conn)
        
        self.pain_df.Time = self.pain_df.Time.apply(self.test.get_datetime) # wont need this line in final
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
        accuracy = accuracy_score(Y_test, Y_pred, normalize =True)
        print("Accuracy is {}".format(accuracy))
        
        
        
              
    
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
        accuracy = accuracy_score(Y_test, Y_pred, normalize =True)
        print("Accuracy is {}".format(accuracy))
