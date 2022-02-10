from sqlalchemy import true
import MeteoCast
from datetime import datetime, date, timedelta
from metpy.units import units
from siphon.simplewebservice.wyoming import WyomingUpperAir
import os,sys
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import pandas as pd
import metpy.calc as mpcalc
from metpy.cbook import get_test_data
from metpy.plots import Hodograph, SkewT
from metpy.units import units
import numpy as np
import io
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import logging
import pylab
from scipy.interpolate import interp1d
from diskcache import Cache
import timeit
import settings
import UpperAtmData as UpperAir
from siphon.catalog import TDSCatalog 
import numpy

def get_sounding(station):
###################################### Collect Sounding ################################################
    cache = settings.AppCache
    #Retrieves Sounding Details and returns them
    
    #If soundings are cached and valid, returns the cache, otherwise retreive new sounding
    key='sounding_'+str(station)
    df = cache.get(key)

    if df is not None:
        #Get sounding from cache and return it
        logging.info("Sounding Cache Hit")
        print("Sounding Cahce Hit")
        return df
    else:

        logging.info("Cache Miss")
        print("Cahce Miss")
        today = datetime.utcnow()
        if today.hour<1:
        #If date is not yet 02:00 make it yesterday... :)
            today = datetime.utcnow() - timedelta(days=1) 
            print("Trying yesterday's sounding data",file=sys.stdout)
        if (today.hour > 13):
            hour = 12
        else:
            hour = 0
        try:
            date = datetime(today.year, today.month, today.day, hour)
            df = WyomingUpperAir.request_data(date, station)
            cache.set(key, df, expire=1800,tag='Sounding Data ')

            #TODO GET LATEST DATE WHEN AVAILABLE
        except Exception as e:
            if (hour==12):
                hour = 0
                print("Unable to retriece 12Z data attempting 00Z data",file=sys.stderr)
                try:
                    date = datetime(today.year, today.month, today.day, hour)
                    station = '40179'
                    df = WyomingUpperAir.request_data(date, station)
                    #TODO GET LATEST DATE WHEN AVAILABLE
                    cache.set(key, df, expire=1800,tag='Sounding Data ')
                except Exception as e:
                    print(e,file=sys.stderr)
                    sys.exit(-1)
               
            else:
                print(e,file=sys.stderr)
                sys.exit(-1)

    return df

def get_forecast(time):
    gfs_catalog=('https://thredds.ucar.edu/thredds/catalog/grib/NCEP/GFS/'
            'Global_0p5deg/catalog.xml?dataset=grib/NCEP/GFS/Global_0p5deg/Best')
    cat = TDSCatalog(gfs_catalog)
    ncss = cat.datasets[0].subset()
    point_query = ncss.query()
    point_query.accept('netcdf4')
    point_query.variables('Temperature_isobaric', 'Relative_humidity_isobaric','u-component_of_wind_isobaric','v-component_of_wind_isobaric','Temperature_surface')
    point_query.lonlat_point(34.43,31.17).time(time)
    data = ncss.get_data(point_query)
    data.variables
    df = pd.DataFrame()
    df["pressure"] = (data['isobaric1'][0][0][20:].tolist()*units.Pa).to(units.hPa)
    df["temperature"] = (data['Temperature_isobaric'][0][0][20:].tolist()*units.degK).to(units.degC)
    hum=data['Relative_humidity_isobaric'][0][0][20:]*units.percent
    u = data['u-component_of_wind_isobaric'][0][0][20:]* (units.meter / units.second)
    v = data['v-component_of_wind_isobaric'][0][0][20:]* (units.meter / units.second)
    p = df['pressure'].values * units.hPa
    T = df['temperature'].values * units.degC
    h=[]
    for i in range(0,len(p)):
        h.append(mpcalc.pressure_to_height_std(p[i]).to(units.ft).magnitude)
    df["height"]=h
    d=[]
    for i in range(0,len(T)):
        d.append(mpcalc.dewpoint_from_relative_humidity(T[i],hum[i]).magnitude)
    df["dewpoint"]=d

    df["humidity"]=data['Relative_humidity_isobaric'][0][0][20:]
    surface_temp = data['Temperature_surface'][0][0]*units.degK
    surface_temp.to(units.degC) 
    ws=[]
    wd=[]
    for i in range(0,len(p)):
        wd.append(mpcalc.wind_direction(u[i],v[i]).magnitude)
        ws.append(mpcalc.wind_speed(u[i],v[i]).to(units.knots).magnitude)
    df["speed"]=ws
    df["direction"]=wd
    data.close()
    return df

def calculate_sounding_data(df,field_height,field_temp):
    ###################################### CALCULATION MAGIC #################################################
    # We will pull the data out of the latest soudning into individual variables and assign units.           #
    # This will Return a dictionary with all the vallculate values. Keys are:                                #
    # "pressure", "temperature", "dewpoint", "height", "windspeed","wind_dir"                               
    ###################################### CALCULATION MAGIC #################################################
    cache = settings.AppCache
    #Retrieves Sounding Details and returns them
    #key='calculation'+str(field_height)+'_'+str(field_temp)
    #If soundings are cached and valid, returns the cache, otherwise retreive new sounding
    #calc = cache.get(key)

    #if calc is not None:
    #    logging.info("Calculation Cache Hit")
    #    print("Calculation Cahce Hit")
    #    return calc
    
    logging.info("Calculation Cache Miss")
    p = df['pressure'].values * units.hPa
    T = df['temperature'].values * units.degC
    Td = df['dewpoint'].values * units.degC
    alt = df['height'].values * units.ft
    wind_speed = df['speed'].values * units.knots
    wind_dir = df['direction'].values * units.degrees
    wet_bulb = mpcalc.wet_bulb_temperature(p,T,Td)
    field_pressure = mpcalc.height_to_pressure_std(field_height*units.ft)
    adiabat_line = mpcalc.dry_lapse(p,field_temp*units.degC,mpcalc.height_to_pressure_std(field_height*units.ft))
    
    #Interpolate Missing Values using linear interpolation
    Td_linear = interp1d(alt.magnitude,Td.magnitude)
    T_linear = interp1d(alt.magnitude,T.magnitude)
    #Calculate the LCL Based on Max Temperature
    lcl_pressure, lcl_temperature = mpcalc.lcl(field_pressure,field_temp*units.degC ,Td_linear(field_height)*units.degC)
    #parcel_prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
    calc = UpperAir.UpperAtmData(df, p, T, Td,alt,wind_speed,wind_dir,wet_bulb,field_pressure,lcl_pressure,lcl_temperature,adiabat_line)
 #   cache.set(key, calc, expire=600,tag='Calculation Data ')
    return calc

    
def calculate_ti(pressure,T_linear,field_temp,field_height):
    Ti = (T_linear([mpcalc.pressure_to_height_std(pressure).to(units.ft).magnitude])[0]*units.degC-mpcalc.dry_lapse(pressure,field_temp*units.degC,mpcalc.height_to_pressure_std(field_height*units.ft))).magnitude
    return Ti


def report(calc,time,field_height,field_temp,rot=0):
    lcl_height=mpcalc.pressure_to_height_std(calc.lcl_pressure).to(units.ft).magnitude
    T_linear = interp1d(calc.alt.magnitude,calc.T.magnitude)
    Ti_lcl = calculate_ti(calc.lcl_pressure,T_linear,field_temp,field_height)
    intersect = mpcalc.find_intersections(calc.p,calc.T,calc.adiabat_line,log_x=true)
    max_value = numpy.max(intersect[0])
    top_of_lift = (mpcalc.pressure_to_height_std(max_value)).to(units.ft).magnitude
    ti5000=calculate_ti(850*units.hPa,T_linear,field_temp,field_height)
    ti10000=calculate_ti(700*units.hPa,T_linear,field_temp,field_height)
    print()
    print("****************************************************************************************")
    print("Soaring forecast for:"+str(time))
    print("Field Temperature: "+str(int(field_temp))+"C")
    print("Top of Useable Lift:" + str(int(top_of_lift))+"ft")
    print("TI @ 5000ft:" + str(ti5000))
    print("TI @ 10000ft:" + str(ti10000))
   
    print("****************************************************************************************")
    # Create a new figure. The dimensions here give a good aspect ratio. Set rotation to 0 to achieve a non-skewet T axis, otherwise set to 30.
    fig = plt.figure(figsize=(12, 12))
    skew = SkewT(fig,rotation=rot)
    
    heights = np.array([1000,2000,3000,4000,5000,6000,7000,8000,9000,10000,11000,12000,13000,14000,15000,16000,17000,18000]) * units.ft
    std_pressures = mpcalc.height_to_pressure_std(heights)
    ###################### DO THE PLOTTING MAGIC ##################################################
    # Plot the data using normal plotting functions, in this case using                           
    # log scaling in Y, as dictated by the typical meteorological plot                              
    ###############################################################################################
    skew.plot(calc.p, calc.T.to(units.degC), 'r', linewidth=2,label='Temperature')
    skew.plot(calc.p, calc.Td, 'g', linewidth=2,label='Dew Point')
    skew.plot(calc.p, calc.wet_bulb.to(units.degC), 'b', linewidth=2,label='Wet Bulb Temperature')
    skew.plot_dry_adiabats()
    skew.plot_moist_adiabats()
    skew.ax.set_ylim(1000,450)
    skew.ax.set_xlim(-30,45)
    skew.ax.set_xticks([-30,-25,-20,-15,-10,-5,0,5,10,15,20,25,30,35,40,45])
    skew.ax.set_yticks([])
    #set aspect ratio for plot
    ratio = 0.3
    xleft, xright = skew.ax.get_xlim()
    ybottom, ytop = skew.ax.get_ylim()
    skew.ax.set_aspect(abs((xright-xleft)/(ybottom-ytop))*1300)
    
    #set height labels
    for height_tick, p_tick in zip(heights, std_pressures):
        trans, _, _ = skew.ax.get_yaxis_text1_transform(0)
        skew.ax.text(-0.08, p_tick, '{:~d}'.format(height_tick), transform=trans)
    # Show the plot
    #ADD Height lines
    for height_tick, p_tick in zip(heights, std_pressures):
        skew.ax.axhline(y=p_tick,color='black',linewidth=0.5)

    #Add base height
    skew.ax.axhline(y=mpcalc.height_to_pressure_std(field_height*units.ft),linewidth=2,label='Field Height',color='black')
    #Relabel Y
    skew.ax.set_ylabel(ylabel="Height",labelpad=50)
    #print(calc.adiabat_line)
    #print(calc.lcl_pressure)
    #add dry adiabatic lapse rate line at the field height and max temperature 
    skew.plot(calc.p,calc.adiabat_line.to(units.degC),'g',linewidth=2,linestyle='--',label='ADLR from Field Max Temp')
       #Add legend
    skew.ax.get_legend_handles_labels()
    skew.ax.legend()
    return plt

def plot_to_png(plt):
    output = io.BytesIO()
    plt.savefig(output,format='png')
    output.seek(0)
    return output.getvalue()
    





