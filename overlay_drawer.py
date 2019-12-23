# -*- coding: utf-8 -*-

'''
                    HUD OVERLAY DRAWER
The script draws telemetry HUD overlay on FPV video. Telemetry data should
be provided as Strava-derived *.gpx track and offset file formed via
moment_track.py script.

Look for Settings section to adjust parameters.

Note that the script is intended to be ran from an IDE (like Spyder or
something like this). It can be called via command line of course, but 
it doesn't accept any command line parameters. So you really SHOULD look
for the Settings section.


DISCLAMER:
The script is really doing what it declared to do, although it's far from
optimized. It's ridiculously slow to be honest. Mostly serves me as a testing
ground for related technologies. Still it does the thing if you're not
expecting fast video processing from a python script.

Prerequisites: pillow, py-opencv, numpy, pandas
'''

import strava_gpx as strava
import pandas as pd
import numpy as np
import cv2
import PIL
import os
import json
from widgets import Speedometer, Map, HeartRate

##########################################################################
def decodeFourcc(cc):
    return ''.join([chr((int(cc) >> 8 * i) & 0xff) for i in range(4)]).upper()
##########################################################################
def pure_pil_alpha_to_color(image, color=(255, 255, 255)):
    '''Alpha composite an RGBA Image with a specified color.
    Source: http://stackoverflow.com/a/9459208/284318
    Keyword Arguments:
    image -- PIL RGBA Image object
    color -- Tuple r, g, b (default 255, 255, 255)
    '''
    image.load()  # needed for split()
    background = PIL.Image.new('RGB', image.size, color)
    background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
    return background
##########################################################################
def readOffsets(finename):
    try:
        with open(finename, 'r') as f:
            fileData = json.load(f)
            dt = pd.to_timedelta(fileData['diffTime'])
            dtMs = int(fileData['diffMS'])
    except:
        dt = pd.to_timedelta('0 days 00:00:00')
        dtMs = 0
    
    return dt, dtMs
##########################################################################
def timeSec(hours, minutes, seconds):
    return int(seconds + 60*minutes + 3600*hours)
##########################################################################
if __name__ == '__main__':
    # ------- Settings -------
    # Input video file name. No strict requirements as long as OpenCV can read it
    videoFileName = 'e:/ph/Sochi-2019/video/2019_0923_123806_025.MOV'

    # Input video start time. Usually comes from file naming of attributes
    videoStartTime = np.datetime64('2019-09-23 12:38:06')

    # Input video start and stop moments (in seconds from start)    
    timingStart = timeSec(hours=0, minutes=13, seconds=11)
    timingEnd   = timeSec(hours=0, minutes=14, seconds=35)
    
    # Input track file name. Should be track saved from Strava via "Export GPX"
    # function (assuming it works the same way as at November 2019)
    trackFileName = 'downhill.gpx'
    
    # Input timing offsets file. The one saved with moment_track.py
    offsetFileName = 'offset.json'

    # Output video vile parameters. Compatibility depends on local OpenCV version
    outFile = 'out.mp4'
    encoding = 'h264'
    
    # Forced output size. Not used if at least one is negative or None
    forcedWidth = None
    forcedHeight = None

    # Widgets
    # Check different IMPLs for a variety of presets
    widgets = [
            Speedometer.IMPL01(pos=(100, 600), scale=1.0),
            Map.IMPL02(pos=(1100, 50), size=(800, 800)),
            HeartRate.IMPL01(pos=(1600, 900), scale=1.0)
            ]
    # ------- End of settings -------
    
    # Clear output file if exists
    if os.path.exists(outFile):
        os.remove(outFile) # Will rise exception if it's a directory

    # Read offsets
    diffTime, diffTimeMS = readOffsets(offsetFileName)

    # Read GPX
    df = strava.readGPX(trackFileName, interpolateToSeconds=False)
    
    # Prepare widgets
    for w in widgets:
        w.prepare(df)
    
    # Open video
    cap = cv2.VideoCapture(videoFileName)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    expectedFrames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    outFPS = cap.get(cv2.CAP_PROP_FPS)
    
    print('File: ', videoFileName)
    print(
        decodeFourcc(cap.get(cv2.CAP_PROP_FOURCC)), '@', '%.0f FPS'%cap.get(cv2.CAP_PROP_FPS),
        ':', width, 'x', height
    )
    print('Frames: ', expectedFrames)
    
    # Check resizing and form the output writer    
    isResizing = (not forcedWidth is None and forcedWidth > 0) and (not forcedHeight is None and forcedHeight > 0)
    if isResizing:
        width = int(forcedWidth)&~1
        height = int(forcedHeight)&~1
    
    fourcc = cv2.VideoWriter_fourcc(*encoding)
    out = cv2.VideoWriter(outFile, fourcc, outFPS, (width, height))
    
    timingPrev = 0

    videoTime = pd.to_datetime(videoStartTime) - diffTime
    
    #  Percentage scaling
    timingScale = 100.0/(timingEnd - timingStart)
    
    while(cap.isOpened()):
        ret, frame = cap.read()
        if not ret:
            break
        
        timingCurMS = cap.get(cv2.CAP_PROP_POS_MSEC) - diffTimeMS
        timingCur = int(timingCurMS/1000)
        
        if not timingPrev == timingCur:
            percentStr = 'skipping to start...'
            if timingCur >= timingStart:
                percentage = int((timingCur - timingStart)*timingScale)
                percentStr = '%d%% complete'%(percentage)
            else:
                percentage = int((timingCur/timingStart)*100) if timingStart > 0 else 100
                percentStr = 'skipping to start... %d%%'%(percentage)
            print('Cur timing: %d of %d to %d (%s)'% (timingCur, timingStart , timingEnd, percentStr))
            timingPrev = timingCur
            
        if timingCur < timingStart:
            continue
        elif timingCur >= timingEnd:
            break
        
        curRec = strava.getRecordForTimeAndOffset(df, videoTime, timingCurMS)
        
        # ocv to pil
        frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        pil_im = PIL.Image.fromarray(frame).convert('RGBA')
        
        # Draw widgets
        for w in widgets:
            w.draw(pil_im, curRec)
        
        # pil to ocv
        if isResizing:
            frame = cv2.resize(np.array(pure_pil_alpha_to_color(pil_im))[:, :, ::-1], (width, height), interpolation=cv2.INTER_AREA)
        else:
            frame = np.array(pure_pil_alpha_to_color(pil_im))[:, :, ::-1]
            #frame = np.array(pure_pil_alpha_to_color(pil_im))[:, :, ::-1].copy()

        # Write frame        
        out.write(frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    
    print('Done.')
