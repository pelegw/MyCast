from datetime import datetime, date, timedelta
import logging
from flask import Flask, render_template, Response
from flask_caching import Cache
import time
from dotenv import load_dotenv
import settings
import ForecastTools
import sqlalchemy as db
import csv
import pandas as pd
import GeoTools
import MeteoCast
import os

if __name__ == "__main__":
    FieldName = 'LLBS'
    start_time = time.time()
    logging.basicConfig(filename='mycast.log',level=logging.DEBUG)
    logging.info("***Starting MyCast***")
    engine = db.create_engine(settings.DB_STRING)
    connection = engine.connect()
    if not engine.dialect.has_table(connection, 'Airports'):  # If table don't exist, Create.
        print("Creating Airports Table")
        metadata = db.MetaData()
        # Create a table with the appropriate Columns
        airports = db.Table('Airports', metadata,
              db.Column('ICAO', db.String(255), primary_key=True, nullable=False), 
              db.Column('Name', db.String(255)), db.Column('City', db.String(255)),
              db.Column('Country', db.String(255)), db.Column('IATA', db.String(255)),
              db.Column('Latitude', db.String(10)),db.Column('Longtitude', db.String(10)),
              db.Column('Elevation', db.String(255)),db.Column('TZDB', db.String(255)))

        # Implement the creation
        metadata.create_all(engine)
        #now populate table
        with open(settings.AirportsFile, newline='',encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                query = db.insert(airports).values(ICAO=row['ICAO'],Name=row['Name'],City=row['City'],Country=row['Country'],Latitude=row['Latitude'],Longtitude=row['Longtitude'],Elevation=row['Elevation'],TZDB=row['TZ Database time']) 
                ResultProxy = connection.execute(query)
    if not engine.dialect.has_table(connection, 'Stations'):  # If table don't exist, Create.
        print("Creating Stations Table")
        metadata = db.MetaData()
        # Create a table with the appropriate Columns
        stations = db.Table('Stations', metadata,
              db.Column('StationNumber', db.String(255), primary_key=True, nullable=False), 
              db.Column('Name', db.String(255)), db.Column('Latitude', db.String(255)),
              db.Column('Longtitude', db.String(255)))

        # Implement the creation
        metadata.create_all(engine)
        #now populate table
        with open(settings.SoundStationsFile, newline='',encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                query = db.insert(stations).values(StationNumber=row['Station Number'],Name=row['Name'],Latitude=row['Lat'],Longtitude=row['Lon'])
                ResultProxy = connection.execute(query)
    
    metadata = db.MetaData()
    fields = db.Table('Airports',metadata, autoload=True, autoload_with=engine)
    query = db.select([fields]).where(fields.columns.ICAO == FieldName)
    ResultProxy = connection.execute(query)
    ResultSet = ResultProxy.fetchall()
    if len(ResultSet)<1:
        print("No Results Found For Field")
        exit()
       #Should be only one result
    field_height = int(ResultSet[0].Elevation)
    field_lat = float(ResultSet[0].Latitude)
    field_lon = float(ResultSet[0].Longtitude)
    #Now we can get the closest sounding station
    #this is a bit crude, but we iterate over each station and find the shortest distance naively.
    stations = db.Table('Stations',metadata, autoload=True, autoload_with=engine)
    query = db.select([stations])
    ResultProxy = connection.execute(query)
    ResultSet = ResultProxy.fetchall()
    min_distance = 20000
    for station in ResultSet:
        station_lat = float(station.Latitude)
        station_lon = float(station.Longtitude)
        distance = GeoTools.get_distance(field_lat,field_lon,station_lat,station_lon)
        if distance < min_distance:
            min_distance = distance
            min_station = station
    station_num = min_station.StationNumber #Field Height 
    #df = MeteoCast.get_sounding(station_num)
    wtime = datetime.utcnow()+timedelta(hours = 12)
    df = MeteoCast.get_forecast(wtime)
    ztemp = ForecastTools.get_temp_by_location_coordinates(field_lat,field_lon,wtime)
    cal = MeteoCast.calculate_sounding_data(df,field_height,ztemp)
    #plt = MeteoCast.get_tskew_plot(cal,field_height,ztemp)
    plt=MeteoCast.report(cal,wtime,field_height,ztemp)
    print("--- %s seconds ---" % (time.time() - start_time))
    plt.show()
    