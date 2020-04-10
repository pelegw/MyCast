
import geopy.distance

def get_distance(lat1,lon1,lat2,lon2):
    #returns distance in km between two points
    point1 = (lat1,lon1)
    point2 = (lat2,lon2)
    return geopy.distance.distance(point1,point2)