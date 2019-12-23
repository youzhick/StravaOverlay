#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
                  STRAVA GPX READING PACK
Not intended for a standalone distribution. Just a helpers collection here.
'''

import pandas as pd
import numpy as np
import math

import xml.etree.ElementTree as etree
##########################################################################
# A little refactored version from Wikipedia Mercator article
def latLon2MercXY(lat, lon):
    if lat > 89.5:
        lat = 89.5
    if lat < -89.5:
        lat = -89.5
 
    rLat = math.radians(lat)
    rLong = math.radians(lon)
 
    a = 6378137.0
    b = 6356752.3142
    f = (a - b)/a
    e = math.sqrt(2*f - f**2)
    x = a*rLong
    y = a*math.log(math.tan(math.pi/4 + rLat/2)*((1 - e*math.sin(rLat))/(1 + e*math.sin(rLat)))**(e/2))
    return (x, y)
##########################################################################
def getDist3D(lat1, lon1, alt1, lat2, lon2, alt2):
    R = 6378.137; 
    dLat = (lat2 - lat1)*math.pi/180;
    dLon = (lon2 - lon1)*math.pi/180;
    a = math.sin(dLat/2)*math.sin(dLat/2) + math.cos(lat1 * math.pi / 180) * math.cos(lat2 * math.pi / 180) * math.sin(dLon/2) * math.sin(dLon/2);
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c * 1000
    dAlt = alt2 - alt1
    return math.sqrt(dAlt**2 + d**2) # in meters
##########################################################################
def getDist2D(lat1, lon1, lat2, lon2):
    R = 6378.137; 
    dLat = (lat2 - lat1)*math.pi/180;
    dLon = (lon2 - lon1)*math.pi/180;
    a = math.sin(dLat/2)*math.sin(dLat/2) + math.cos(lat1 * math.pi / 180) * math.cos(lat2 * math.pi / 180) * math.sin(dLon/2) * math.sin(dLon/2);
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c
    return d * 1000 # in meters
##########################################################################
def readGPX(filename, setTimeIndex=True, interpolateToSeconds=False):
    tree = etree.parse(filename)
    
    pts = tree.findall('{http://www.topografix.com/GPX/1/1}trk')[0].findall('{http://www.topografix.com/GPX/1/1}trkseg')[0].findall('{http://www.topografix.com/GPX/1/1}trkpt')
    recs = []
    prevLat, prevLon = None, None
    prevTimeStamp = None
    prevEle = None
    for pt in pts:
        try:
            time = np.datetime64(pt.findall('{http://www.topografix.com/GPX/1/1}time')[0].text.replace('Z', ''))
        except:
            time = np.datetime64(0)
        timestamp = int((time - np.datetime64('1970-01-01T00:00:00')) / np.timedelta64(1, 's'))

        try:
            power = float(pt.findall('{http://www.topografix.com/GPX/1/1}extensions')[0].findall('{http://www.topografix.com/GPX/1/1}power')[0].text)
        except:
            power = 0.0
        try:
            cadence = int(pt.findall('{http://www.topografix.com/GPX/1/1}extensions')[0].findall('{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}TrackPointExtension')[0].findall('{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}cad')[0].text)
        except:
            cadence = 0;
        try:
            hr = int(pt.findall('{http://www.topografix.com/GPX/1/1}extensions')[0].findall('{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}TrackPointExtension')[0].findall('{http://www.garmin.com/xmlschemas/TrackPointExtension/v1}hr')[0].text)
        except:
            hr = 0
        try: 
            ele = float(pt.findall('{http://www.topografix.com/GPX/1/1}ele')[0].text)
        except:
            ele = 0
        try:
            lat = float(pt.attrib['lat'])
            lon = float(pt.attrib['lon'])
        except:
            lat = 0.0
            lon = 0.0
        try:
            x, y = latLon2MercXY(lat, lon)
        except:
            x, y = (0, 0)
            
        try:
            d = getDist3D(prevLat, prevLon, prevEle, lat, lon, ele)/1000
            dt = (timestamp - prevTimeStamp)/3600.0
            vel = d/dt
        except:
            vel = 0
        
        prevLat = lat
        prevLon = lon
        prevEle = ele
        prevTimeStamp = timestamp
        
        recs.append({'time': time, 'timestamp': timestamp, 'power': power, 'cadence': cadence, 'hr': hr, 'ele': ele, 'lat': lat, 'lon': lon, 'x': x, 'y': y, 'vel': vel, 'vel_filt': vel})
        pass
    
    filterRadius = 1
    for i in range(filterRadius, len(recs) - filterRadius - 1):
        try:
            lat1 = recs[i - filterRadius]['lat']
            lat2 = recs[i + filterRadius]['lat']
            lon1 = recs[i - filterRadius]['lon']
            lon2 = recs[i + filterRadius]['lon']
            ele1 = recs[i - filterRadius]['ele']
            ele2 = recs[i + filterRadius]['ele']
            t1 = recs[i - filterRadius]['timestamp']
            t2 = recs[i + filterRadius]['timestamp']
            dt = (t2 - t1)/3600.0
            d = getDist3D(lat1, lon1, ele1, lat2, lon2, ele2)/1000
            recs[i]['vel_filt'] = d/dt
        except:
            pass
    
    result = pd.DataFrame(recs);
    #result['vel_filt'] = result['vel'].rolling(window=3).mean()
    
    if (setTimeIndex):
        result.set_index(pd.DatetimeIndex(result['time']), inplace=True)
        
    return result if not interpolateToSeconds else result.reindex(pd.date_range(start=result.index.min(), end=result.index.max(), freq='1S')).interpolate(method='linear')
##########################################################################
def getRecordForTime(data, time):
    try:
        return data.loc[pd.to_datetime(time)]
    except: 
        return data.iloc[data.index.get_loc(pd.to_datetime(time), method='nearest')]
##########################################################################
def interp(v1, v2, d, d1):
    dv = v2 - v1
    return (v1 + dv*d1/d)
##########################################################################
def getRecordForTimeAndOffset(data, time, timeOffsetMS):

    t = pd.to_datetime(time, unit='ms') + pd.to_timedelta(timeOffsetMS, unit='ms')
    try:
        
        d1 = data.iloc[data.index.get_loc(t, method='pad')]
        d2 = data.iloc[data.index.get_loc(t, method='backfill')]
        
        if (d1['timestamp'] == d2['timestamp']):
            return d1
        
        t1 = pd.to_datetime(d1['time'], unit='ms')
        t2 = pd.to_datetime(d2['time'], unit='ms')
        dt = (t2 - t1).total_seconds()*1000
        dt1 = (t - t1).total_seconds()*1000
        
        res = d1.copy()
        res['x'] = interp(d1['x'], d2['x'], dt, dt1)
        res['y'] = interp(d1['y'], d2['y'], dt, dt1)
        res['cadence'] = interp(d1['cadence'], d2['cadence'], dt, dt1)
        res['ele'] = interp(d1['ele'], d2['ele'], dt, dt1)
        res['hr'] = interp(d1['hr'], d2['hr'], dt, dt1)
        res['lat'] = interp(d1['lat'], d2['lat'], dt, dt1)
        res['lon'] = interp(d1['lon'], d2['lon'], dt, dt1)
        res['power'] = interp(d1['power'], d2['power'], dt, dt1)
        res['time'] = t
        res['timestamp'] = interp(d1['timestamp'], d2['timestamp'], dt, dt1)
        res['vel'] = interp(d1['vel'], d2['vel'], dt, dt1)
        res['vel_filt'] = interp(d1['vel_filt'], d2['vel_filt'], dt, dt1)
        
    except:
        print('Warning: Timestamp is out of dataframe')
        res = data.iloc[0] if t < data.iloc[0]['time'] else data.iloc[-1]
        
    return res
    
##########################################################################
if __name__ == '__main__':
    # Test section
    df = readGPX('downhill.gpx', interpolateToSeconds=False)
    print (df)
    
    print('Vel     : ', df['vel'].min(), df['vel'].max())
    print('Vel_filt: ', df['vel_filt'].min(), df['vel_filt'].max())
    
    tm = np.datetime64('2019-09-23 13:16:37')
    tm2 = np.datetime64('2019-09-23 14:16:37')
    d = (tm2 - tm).item().total_seconds()
    print(d, type(d))
    print(tm)
    rec = getRecordForTime(df, tm)
    
    #print('----')
    #rec1 = getRecordForTimeAndOffset(df, pd.to_datetime(tm), 341)
    #print(rec1)

    print(rec)
    #print((df.iloc[-1].time - df.iloc[0].time).total_seconds())
    #print(df.iloc[-1].time.second)
    