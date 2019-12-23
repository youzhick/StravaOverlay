# -*- coding: utf-8 -*-

'''
                TRACK SYNCHRONIZATION
The script helps to find real time offset between Strava-derived *.gpx track
and an improperly timestamped video.

Look for Settings section to adjust parameters and key bindings.

Note that the script is intended to be ran from an IDE (like Spyder or
something like this). It can be called via command line of course, but 
it doesn't accept any command line parameters. So you really SHOULD look
for the Settings section.

DISCLAMER:
The script is really doing what it declared to do, although it's far from
optimized or UI/UX polished. Mostly serves me as a testing ground for related
technologies. Still it does the thing.

Prerequisites: py-opencv, numpy, pandas

HOW TO USE:
    The main idea is to play video and on-map-painted position independently
and stop both at a moment you can definitely say "that's the same moment for
both". It may be some kind of sharp turn for example: you can see your pointer
on the map passing this torn and you can identify it on the video.
    First visit the Settings section, review it and don't forget to fill
[videoStartTime].  This is an approximate video start time. Most probably your
camera names the files somewhat like "2019_0923_123806_025.MOV", which means
start time "2019-09-23 12:38:06". Don't worry if the camera clock is off by
some minutes or time zone isn't set correctly: this is the kind of offsets
the script is intended to find.
    Right after the start both video and map will be animated, but note that
these are NOT synchronized and are running at a different speeds. So you may
want to stop one for starter and return to it later. See "Key bindings"
subsection of the Settings section to find out the streams control keys. These
should be quite obvious: both can be paused/unpaused or moved one step forward
(when on pause). Map view can also be moved one step backward, while video have
additional option the skip several steps .
    When you think both streams are paused at the same moment, hit [KEY_SAVE]
key ("Enter" by default) and you'll receive the saved offset in
[offsetFileName] json file. You'll have to provide this file name
to overlay_drawer.py later.
    Note that one step of video stream is one frame (it's 1/30 or even 1/60 s),
while the track step most probably is 1 s. Thus good idea to fine-tune
the streams alignment  with the video stream, not the track one.
    
'''

import strava_gpx as strava
import pandas as pd
import numpy as np
import json
import cv2

##########################################################################
'''
scale - input dictionary
input area: (srcW * srcH), startimg from minX, minY
output area: (dstW * dstH), starting from startX, startY
'''
def ptScale(scaler, point):
    _scaleX = scaler['dstW']/scaler['srcW']
    _scaleY = scaler['dstH']/scaler['srcH']
    if scaler['keepAspect']:
        _scale = min(_scaleX, _scaleY)
        _scaleX = _scale
        _scaleY = _scale
    _offsX = (scaler['dstW'] - scaler['srcW']*_scaleX)/2
    _offsY = (scaler['dstH'] - scaler['srcH']*_scaleY)/2
    
    return (int(scaler['startX'] + _offsX + (point[0] - scaler['minX'])*_scaleX), 
            int(scaler['startY'] + _offsY + (point[1] - scaler['minY'])*_scaleY))
##########################################################################
if __name__ == '__main__':
    # ------- Settings -------
    
    # Input track file name. Should be track saved from Strava via "Export GPX"
    # function (assuming it works the same way as at November 2019)
    trackFileName = 'downhill.gpx'
    
    # Input video file name. No strict requirements as long as OpenCV can read it
    videoFileName = 'e:/ph/Sochi-2019/video/2019_0923_123806_025.MOV'
    
    # Output file for resulting offset
    offsetFileName = 'offset.json'
    
    # Video start time. Usually comes from file naming of attributes
    videoStartTime = np.datetime64('2019-09-23 12:38:06')
    
    # Displaying parameters
    
    # On-screen image size (consider it window size)
    imageSize = (1600, 1100)
    
    # Additional scaling of the of the zoomed window.
    # Probably you don't need to change this.
    zoomScale = 1.0
    
    # Zoomed window size and position
    zoomedSize = (400, 300)
    zoomedPos = (100, 100)

    # Video window size and position
    videoFitSize = (300, 300)
    videoWindowPos = (100, 600)
    
    # Key bindings
    KEY_QUIT                = ord('q') # Q
    KEY_SAVE                = 13       # <Enter>
    KEY_PAUSE_TRACK         = ord('p') # P
    KEY_PAUSE_VIDEO         = ord(' ') # <Space>
    KEY_TRACK_STEP_FORWARD  = ord('=') # +
    KEY_TRACK_STEP_BACK     = ord('-') # -
    KEY_VIDEO_NEXT_FRAME    = ord('z') # Z
    KEY_VIDEO_SKIP_N_FRAMES = ord('x') # X
    frames2skipN = 30
    # ------- End of settings -------
    
    df = strava.readGPX(trackFileName, interpolateToSeconds=False)
    
    cap = cv2.VideoCapture(videoFileName)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    scaleX = float(videoFitSize[0])/width
    scaleY = float(videoFitSize[1])/height
    scale = min(scaleX, scaleY)
    videoSize = (int(width*scale), int(height*scale))
    

    print('HR: ', df['hr'].min(), ':', df['hr'].max())

    minX = df['x'].min()
    maxX = df['x'].max()
    minY = df['y'].min()
    maxY = df['y'].max()

    scaler = {}
    scaler['minX'] = minX
    scaler['minY'] = minY
    scaler['srcW'] = maxX - minX
    scaler['srcH'] = maxY - minY
    scaler['startX'] = -200
    scaler['startY'] = 0
    scaler['dstW'] = imageSize[0]
    scaler['dstH'] = imageSize[1]
    scaler['keepAspect'] = True
    print('Map area: ', scaler['srcW'], 'x', scaler['srcH'])
    
    
    mapFrame = np.ndarray((imageSize[1], imageSize[0], 3), dtype=np.uint8)
    mapFrame.fill(0)

    zoomedW = int(zoomScale*10000)
    zoomedH = int(zoomScale*10000)
    zoomedMap = np.ndarray((zoomedH, zoomedW, 3), dtype=np.uint8)
    zoomedMap.fill(0)
    zoomScaler = scaler.copy()
    scaler['startX'] = 0
    scaler['startY'] = 0
    zoomScaler['dstW'] = zoomedW
    zoomScaler['dstH'] = zoomedH
    
    
    print('Building map')
    prevX = None
    prevY = None
    prevZoomX = None
    prevZoomY = None
    for ind, row in df.iterrows():
        # Normal map
        x, y = ptScale(scaler, (row['x'], row['y']))
        y = imageSize[1] - y
        if not prevX == None and not prevY == None:
            cv2.line(mapFrame, (x, y), (prevX, prevY), [255, 255, 255], thickness=1, lineType=cv2.LINE_AA)
        prevX = x
        prevY = y

        # Zoomed map
        zx, zy = ptScale(zoomScaler, (row['x'], row['y']))
        zy = zoomedH - zy
        if not prevZoomX == None and not prevZoomY == None:
            cv2.line(zoomedMap, (zx, zy), (prevZoomX, prevZoomY), [255, 255, 255], thickness=1, lineType=cv2.LINE_AA)
        prevZoomX = zx
        prevZoomY = zy
    
    #cv2.imwrite('map.jpg', mapFrame)
    #cv2.imwrite('map_big.jpg', zoomedMap)

    print('Displaying map')
    videoFrameInd = -1
    
    zoomedPosX = zoomedPos[0]
    zoomedPosY = zoomedPos[1]
    zoomedRX = int(zoomedSize[0]/2)
    zoomedRY = int(zoomedSize[1]/2)
    zoomDX = zoomedRX*2
    zoomDY = zoomedRY*2
    
    ind = 0
    isPausedTrack = False
    isPausedVideo = False
    isFinishedVideo = not cap.isOpened()
    videoFrame = None
    resizedVideoFrame = None
    while True:
        # Track step
        if not isPausedTrack and ind < df.shape[0] - 2:
            ind += 1
        row = df.iloc[ind]
        # Video step
        if (not isFinishedVideo) and ((videoFrame is None) or not isPausedVideo):
            ret, videoFrame = cap.read()
            isFinishedVideo = not ret
            if not isFinishedVideo:
                resizedVideoFrame = cv2.resize(videoFrame, videoSize, interpolation=cv2.INTER_AREA)
                videoFrameInd += 1
        
        x, y = ptScale(scaler, (row['x'], row['y']))
        y = imageSize[1] - y

        # Draw main map
        curFrame = mapFrame.copy()
        cv2.circle(curFrame, (x, y), 5, [255, 255, 255], thickness=3, lineType=cv2.LINE_AA)

        # Draw zoomed
        xx, yy = ptScale(zoomScaler, (row['x'], row['y']))
        yy = zoomedH - yy
        zShiftX = 0
        zShiftY = 0
        zoomedStartX = xx - zoomedRX
        zoomedStartY = yy - zoomedRY
        if zoomedStartX < 0:
            zShiftX = -zoomedStartX
            zoomedStartX = 0
        elif zoomedStartX + zoomDX >= zoomedW:
            zShiftX = zoomedW - zoomDX - zoomedStartX - 1
            zoomedStartX = zoomedStartX + zShiftX
        if zoomedStartY < 0:
            zShiftY = -zoomedStartY
            zoomedStartY = 0
        elif zoomedStartY + zoomDY >= zoomedH:
            zShiftY = zoomedH - zoomDY - zoomedStartY - 1
            zoomedStartY = zoomedStartY + zShiftY
        curFrame[zoomedPosY:(zoomDY + zoomedPosY):, zoomedPosX:(zoomDX + zoomedPosX):, ::] = zoomedMap[zoomedStartY:(zoomDY + zoomedStartY):, zoomedStartX:(zoomDX + zoomedStartX):, ::]
        cv2.rectangle(curFrame, (zoomedPosX, zoomedPosY), (zoomedPosX + zoomDX, zoomedPosY + zoomDY), [255, 0, 0], thickness=3, lineType=cv2.LINE_AA)
        cv2.circle(curFrame, (zoomedPosX + zoomedRX - zShiftX, zoomedPosY + zoomedRY - zShiftY), 5, [255, 255, 255], thickness=3, lineType=cv2.LINE_AA)
        
        # Draw video frame
        if not resizedVideoFrame is None:
            curFrame[videoWindowPos[1]:(videoWindowPos[1] + videoSize[1]):, videoWindowPos[0]:(videoWindowPos[0] + videoSize[0]):, ::] = resizedVideoFrame
        
        cv2.imshow('frame',curFrame)
        
        # Keyboard handling
        key = cv2.waitKey(1)
        if key & 0xFF == KEY_QUIT:
            break
        elif key & 0xFF == KEY_PAUSE_TRACK:
            isPausedTrack = not isPausedTrack
        elif key & 0xFF == KEY_PAUSE_VIDEO:
            isPausedVideo = not isPausedVideo
        elif key & 0xFF == KEY_TRACK_STEP_FORWARD:
            if isPausedTrack and ind < df.shape[0] - 2:
                ind += 1
        elif key & 0xFF == KEY_TRACK_STEP_BACK:
            if isPausedTrack and ind > 0:
                ind -= 1
        elif key & 0xFF == KEY_VIDEO_NEXT_FRAME:
            if isPausedVideo and (not isFinishedVideo):
                ret, videoFrame = cap.read()
                isFinishedVideo = not ret
                if not isFinishedVideo:
                    resizedVideoFrame = cv2.resize(videoFrame, videoSize, interpolation=cv2.INTER_AREA)
                    videoFrameInd += 1
        elif key & 0xFF == KEY_VIDEO_SKIP_N_FRAMES:
            for i in range(frames2skipN):
                if isPausedVideo and (not isFinishedVideo):
                    ret, videoFrame = cap.read()
                    isFinishedVideo = not ret
                    videoFrameInd += 1
            if not isFinishedVideo:
                resizedVideoFrame = cv2.resize(videoFrame, videoSize, interpolation=cv2.INTER_AREA)
        elif key & 0xFF == KEY_SAVE:
            print('Syncing...')
            trackTime = row['time']
            videoTime = pd.to_datetime(videoStartTime + int(cap.get(cv2.CAP_PROP_POS_MSEC)/1000))
            print('Track time:', trackTime)
            print('Video time:', videoTime)

            #diffTime = trackTime - videoTime
            diffTime = videoTime - trackTime
            diffMS = int(cap.get(cv2.CAP_PROP_POS_MSEC) % 1000)
            
            print('Current time diff:', diffTime, '+', diffMS, "MS")
            print('Saved   time diff:', diffTime)
            print('Corrected video time:', videoTime + diffTime)
            print('Video frame index:', videoFrameInd)
            print('Track point index:', ind)
            
            try:
                with open(offsetFileName, 'w') as f:
                    json.dump({'diffTime': str(diffTime), 'diffMS': diffMS}, f)
                    print('Offset saved to ' + offsetFileName)
            except:
                print('Error saving ' + offsetFileName)
                
    cap.release()
    cv2.destroyAllWindows()
    print('Done.')
