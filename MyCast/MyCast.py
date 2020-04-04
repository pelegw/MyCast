import MeteoCast
import logging
from flask import Flask, render_template, Response
from flask_caching import Cache

if __name__ == "__main__":
    logging.basicConfig(filename='mycast.log',level=logging.DEBUG)
    logging.info("***Starting***")
    logging.info("PNG Export Request")
     #create a date object for today
    field_height = 650 #Field Height for Sde Teman Airfield
    field_temp = 31 #Field Max Temp in degC
    station = '40179' #Field Height
    df = MeteoCast.get_sounding(station)
    cal = MeteoCast.calculate_sounding_data(df,field_height,field_temp)
    plt = MeteoCast.get_tskew_plot(cal,field_height,field_temp)
    plt.show()
