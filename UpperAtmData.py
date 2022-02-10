import metpy.calc as mpcalc
#Define a class for passing all calculation values
class UpperAtmData:
    def __init__(self, df, p, T, Td,alt,wind_speed,wind_dir,wet_bulb,field_pressure,lcl_pressure,lcl_temperature,adiabat_line):
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
        self.adiabat_line = adiabat_line

    def get_wind_components(self):
        u, v = mpcalc.wind_components(self.wind_speed, self.wind_dir)