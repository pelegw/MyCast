import settings
import requests
from diskcache import Cache
import logging


def get_weather_by_location_name(location):
    #generate cache key
    cache = settings.AppCache
    key = "Weather_"+location
    fc = cache.get(key)
    if fc is not None:
        logging.info("Forecast Cache Hit")
        return fc
    
    logging.info("Forecast Cache Miss")
    url = settings.OWMCurretWeatherEndpoint+"?q={}&units=metric&appid={}".format(location, settings.OpenWeatherMapKey)
    r = requests.get(url)
    cache.set(key, r.json(), expire=10800,tag='Forecast Data ')
    return r.json()

def get_weather_by_location_coordinates(lat,lon):
    cache = settings.AppCache
    key = "Weather_"+str(lat)+'_'+str(lon)
    fc = cache.get(key)
    if fc is not None:
        logging.info("Forecast Cache Hit")
        return fc
    logging.info("Forecast Cache Miss")
    url = settings.OWMCurretWeatherEndpoint+"?lat={}&lon={}&units=metric&appid={}".format(str(lat),str(lon), settings.OpenWeatherMapKey)
    r = requests.get(url)
    cache.set(key, r.json(), expire=10800,tag='Forecast Data ')
    return r.json()

def get_forecast_by_location_name(location):
    #generate cache key
    cache = settings.AppCache
    key = "Forecast_"+location
    fc = cache.get(key)
    if fc is not None:
        logging.info("Forecast Cache Hit")
        return fc
    
    logging.info("Forecast Cache Miss")
    url = settings.OWMForecastEndpoint+"?q={}&units=metric&appid={}".format(location, settings.OpenWeatherMapKey)
    r = requests.get(url)
    cache.set(key, r.json(), expire=10800,tag='Forecast Data ')
    return r.json()

def get_forecast_by_location_coordinates(lat,lon):
    cache = settings.AppCache
    key = "Forecast_"+str(lat)+'_'+str(lon)
    fc = cache.get(key)
    if fc is not None:
        logging.info("Forecast Cache Hit")
        return fc
    logging.info("Forecast Cache Miss")
    url = settings.OWMForecastEndpoint+"?lat={}&lon={}&units=metric&appid={}".format(str(lat),str(lon), settings.OpenWeatherMapKey)
    r = requests.get(url)
    cache.set(key, r.json(), expire=10800,tag='Forecast Data ')
    return r.json()