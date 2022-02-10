import settings
import requests
from diskcache import Cache
import logging
from metpy.units import units
import metpy.calc as mpcalc
from datetime import datetime, date, timedelta
import os

def get_onecall_api(lat,lon):
    #Make a OneCallAPI call and cache results
    #generate cache key 
    cache = settings.AppCache
    key = "Weather_"+str(lat)+'_'+str(lon)
    fc = cache.get(key)
    if fc is not None:
        logging.info("Forecast Cache Hit")
        return fc
    
    logging.info("Forecast Cache Miss")
    print("Endpoint: "+settings.OWMFOneCallAPIEndpoint)
    url = settings.OWMFOneCallAPIEndpoint+"?lat={}&lon={}&exclude=current,minutely,alertrs&appid={}".format(str(lat),str(lon), os.environ.get("OpenWeatherMapAPIKey"))
    r = requests.get(url)
    cache.set(key, r.json(), expire=3600,tag='Forecast Data ')
    return r.json()

def get_temp_by_location_coordinates(lat,lon,time):
    print("Locations "+str(lat)+","+str(lon))
    cache = settings.AppCache
    key = "Weather_"+str(lat)+'_'+str(lon)
    fc = cache.get(key)
    if fc is not None:
        logging.info("Forecast Cache Hit")
        hit = True
    else:
        hit = False
        logging.info("Forecast Cache Miss")
    if not hit:
        fc = get_onecall_api(lat,lon) 
    weather = fc
    index=int((time - datetime.utcnow()).total_seconds()//3600)
    temp=(weather['hourly'][index]['temp']*units.degK).to(units.degC)
    return temp.magnitude

