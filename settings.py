import os
from os.path import join, dirname
from dotenv import load_dotenv
from diskcache import Cache
import csv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
OpenWeatherMapKey = os.environ.get("OpenWeatherMapAPIKey")
OWMCurretWeatherEndpoint = os.environ.get("OWMCurretWeatherEndpoint")
OWMForecastEndpoint = os.environ.get("OWMForecastEndpoint")
OWMFOneCallAPIEndpoint = os.environ.get("OWMOneCallEndpoint")
AppCache = Cache("./data")
SoundStationsFile = "./data/sounding_stations.csv"
AirportsFile = "./data/airports.csv"
DB_STRING = 'sqlite:///data/MyCast.sqlite'