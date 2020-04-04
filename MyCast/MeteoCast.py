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
#Create Date/Time and Location object
import numpy as np
import io
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from PIL import Image
import logging
import pylab
from scipy.interpolate import interp1d
from diskcache import Cache

#Define a class for passing all calculation values
class UpperAtmData:
    def __init__(self, df, p, T, Td,alt,wind_speed,wind_dir,wet_bulb,field_pressure,lcl_pressure,lcl_temperature):
        self.df = df
        self.p = p
        self.T = T
        self.Td = Td
        self.alt = alt
        self.wind_speed = wind_speed
        self.wind_dir = wind_dir
        self.wet_bulb = wet_bulb
        self.field_pressure = field_pressure
        self.lcl_pressure = lcl_pressure
        self.lcl_temperature = lcl_temperature
    def get_wind_components(self):
        u, v = mpcalc.wind_components(self.wind_speed, self.wind_dir)

def get_sounding(station):
###################################### Collect Sounding ################################################
    cache = Cache("./")
    #Retrieves Sounding Details and returns them
    
    #If soundings are cached and valid, returns the cache, otherwise retreive new sounding
    df = cache.get('sounding')
    print(df)
    if not df.empty:
        #Get sounding from cache and return it
        logging.info("Cache Hit")
        print("Cahce Hit")
        return df
    else:

        logging.info("Cache Miss")
        print("Cahce Miss")
        today = datetime.today()
        if today.hour<3:
        #If date is not yet 02:00 make it yesterday... :)
            today = datetime.now() - timedelta(days=1) 
            print("Trying yesterday's sounding data",file=sys.stdout)
        if (today.hour > 13):
            hour = 12
        else:
            hour = 0
        try:
            date = datetime(today.year, today.month, today.day, hour)
            #date = datetime(2020, 3, 14, 0)
        
            df = WyomingUpperAir.request_data(date, station)
            #TODO GET LATEST DATE WHEN AVAILABLE
        except Exception as e:
            if (hour==12):
                hour = 0
                print("Unable to retriece 12Z data attempting 00Z data",file=sys.stderr)
                try:
                    date = datetime(today.year, today.month, 1, hour)
                    station = '40179'
                    df = WyomingUpperAir.request_data(date, station)
                    #TODO GET LATEST DATE WHEN AVAILABLE
                    cache.set('sounding', df, expire=600,tag='Sounding Data ')
                except Exception as e:
                    print(e,file=sys.stderr)
                    sys.exit(-1)
               
            else:
                print(e,file=sys.stderr)
                sys.exit(-1)

    return df



def calculate_sounding_data(df,field_height,field_temp):
    ###################################### CALCULATION MAGIC #################################################
    # We will pull the data out of the latest soudning into individual variables and assign units.           #
    # This will Return a dictionary with all the vallculate values. Keys are:                                #
    # "pressure", "temperature", "dewpoint", "height", "windspeed","wind_dir"                               
    ###################################### CALCULATION MAGIC #################################################
    p = df['pressure'].values * units.hPa
    T = df['temperature'].values * units.degC
    Td = df['dewpoint'].values * units.degC
    alt = df['height'].values * units.ft
    wind_speed = df['speed'].values * units.knots
    wind_dir = df['direction'].values * units.degrees
    wet_bulb = mpcalc.wet_bulb_temperature(p,T,Td)
    field_pressure = mpcalc.height_to_pressure_std(field_height*units.ft)
    
    #Interpolate Missing Values using linear interpolation
    Td_linear = interp1d(alt.magnitude,Td.magnitude)
    T_linear = interp1d(alt.magnitude,T.magnitude)
    
    #Calculate the LCL Based on Max Temperature
    lcl_pressure, lcl_temperature = mpcalc.lcl(field_pressure,field_temp*units.degC ,Td_linear(field_height)*units.degC)
    #parcel_prof = mpcalc.parcel_profile(p, T[0], Td[0]).to('degC')
    return MeteoCast.UpperAtmData(df, p, T, Td,alt,wind_speed,wind_dir,wet_bulb,field_pressure,lcl_pressure,lcl_temperature)


def get_tskew_plot(calc,field_height,field_temp,rot=0):
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
    skew.ax.set_xlim(-40,50)
    skew.ax.set_xticks([-40,-35,-30,-25,-20,-15,-10,-5,0,5,10,15,20,25,30,35,40,45,50])
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

    #add dry adiabatic lapse rate line at the field height and max temperature 
    adiabat = mpcalc.dry_lapse(calc.p,field_temp*units.degC,ref_pressure=mpcalc.height_to_pressure_std(field_height*units.ft))
    skew.plot(calc.p,adiabat,'g',linewidth=1,linestyle='--')
       #Add legend
    skew.ax.get_legend_handles_labels()
    skew.ax.legend()
    return plt

def plot_to_png(plt):
    output = io.BytesIO()
    plt.savefig(output,format='png')
    output.seek(0)
    return output.getvalue()




