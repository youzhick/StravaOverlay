# -*- coding: utf-8 -*-

import PIL
from PIL import ImageDraw, ImageFont
import moment_track as moment

##########################################################################
class Widget:
    def __init__(self):
        pass
    def draw(self, img, dataRecord):
        pass
    def prepare(self, fullData):
        pass
    def clear(self):  
        pass
    def __del__(self):    
        try:
            self.clear()
        except:
               pass 
##########################################################################
class Map (Widget):
    def __init__(self, lineWidthInner, lineWidthOuter, pointerRadius):
        Widget.__init__(self)
        self.lineWidthInner = lineWidthInner
        self.lineWidthOuter = lineWidthOuter
        self.pointerRadius = pointerRadius
# ------------------------------------------------------------------------
    def getCurMap(self, rec):
        curMap = self.mapImg.copy()
        x, y = moment.ptScale(self.scaler, (rec['x'], rec['y']))
        y = curMap.size[1] - y
        
        r = self.pointerRadius
        draw = ImageDraw.Draw(curMap)
        draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(255, 0, 0, 255), width=6)
        del draw
        
        return curMap
# ------------------------------------------------------------------------
    def prepare(self, fullData):
        Widget.prepare(self, fullData)
        self.scaler = {}
        minX = fullData['x'].min()
        maxX = fullData['x'].max()
        minY = fullData['y'].min()
        maxY = fullData['y'].max()
        self.scaler['minX'] = minX
        self.scaler['minY'] = minY
        self.scaler['srcW'] = maxX - minX
        self.scaler['srcH'] = maxY - minY
        self.scaler['startX'] = 0
        self.scaler['startY'] = 0
        self.scaler['dstW'] = self.size[0]
        self.scaler['dstH'] = self.size[1]
        self.scaler['keepAspect'] = True

        self.mapImg = PIL.Image.new('RGBA', self.size, (0, 0, 0, 0))
        
        draw = ImageDraw.Draw(self.mapImg)
        
        prevX = None
        prevY = None
        for ind, row in fullData.iterrows():
            # Normal map
            x, y = moment.ptScale(self.scaler, (row['x'], row['y']))
            y = self.size[1] - y
            if not prevX == None and not prevY == None:
                draw.line([(x, y), (prevX, prevY)], fill=(0, 0, 0, 155), width=self.lineWidthOuter)
            prevX = x
            prevY = y
        prevX = None
        prevY = None
        for ind, row in fullData.iterrows():
            # Normal map
            x, y = moment.ptScale(self.scaler, (row['x'], row['y']))
            y = self.size[1] - y
            if not prevX == None and not prevY == None:
                draw.line([(x, y), (prevX, prevY)], fill=(255, 255, 255, 200), width=self.lineWidthInner)
            prevX = x
            prevY = y
        del draw
# ------------------------------------------------------------------------
    def draw(self, img, dataRecord):
        curMap = self.getCurMap(dataRecord)
        img.paste(curMap, self.pos, curMap)
        del curMap
# ------------------------------------------------------------------------
    def position(self, pos, size):
        self.pos = pos
        self.size = size
# ------------------------------------------------------------------------
    def clear(self):    
        del self.mapImg
        Widget.clear(self)
# ------------------------------------------------------------------------
    def IMPL01(pos, size):
        mp = Map(lineWidthInner=2, lineWidthOuter=6, pointerRadius=8)
        mp.position(pos, size)
        return mp
# ------------------------------------------------------------------------
    def IMPL02(pos, size):
        mp = Map(lineWidthInner=4, lineWidthOuter=8, pointerRadius=10)
        mp.position(pos, size)
        return mp
# ------------------------------------------------------------------------
    def IMPL03(pos, size):
        mp = Map(lineWidthInner=8, lineWidthOuter=16, pointerRadius=10)
        mp.position(pos, size)
        return mp
##########################################################################
class Speedometer (Widget):
    def __init__(self, boardFile, arrowFile, topwardSpeedValueKmh, kmh2degScale, minValKmh, maxValKmh):
        Widget.__init__(self)
        self.speed_im = PIL.Image.open(boardFile)
        self.arrow_im = PIL.Image.open(arrowFile)
        self.topwardSpeedValueKmh = topwardSpeedValueKmh
        self.kmh2degScale = kmh2degScale
        self.minValKmh = minValKmh
        self.maxValKmh = maxValKmh
# ------------------------------------------------------------------------
    def draw(self, img, dataRecord):
        speed = dataRecord['vel_filt']
        if speed < self.minValKmh:
            speed = self.minValKmh
        if speed > self.maxValKmh:
            speed = self.maxValKmh
        
        angle = -float(speed - self.topwardSpeedValueKmh)*self.kmh2degScale

        img.paste(self.speed_im, self.pos, self.speed_im)
        arr_im = self.arrow_im.rotate(angle)
        img.paste(arr_im, self.pos, arr_im)
        
        del arr_im
# ------------------------------------------------------------------------
    def position(self, pos, scale=1.0):
        if not scale == 1.0:
            self.speed_im = self.speed_im.resize((int(self.speed_im.size[0]*scale), int(self.speed_im.size[1]*scale)), resample=PIL.Image.LANCZOS)
            self.arrow_im = self.arrow_im.resize((int(self.arrow_im.size[0]*scale), int(self.arrow_im.size[1]*scale)), resample=PIL.Image.LANCZOS)
        self.pos = pos
# ------------------------------------------------------------------------
    def clear(self):    
        del self.speed_im
        del self.arrow_im
        Widget.clear(self)
# ------------------------------------------------------------------------
    def IMPL01(pos, scale=1.0):
        spd = Speedometer(
                boardFile='images/speedometer1.png', 
                arrowFile='images/speed_arrow1.png', 
                topwardSpeedValueKmh=40, 
                kmh2degScale=90/30,
                minValKmh=0,
                maxValKmh=85
                )
        spd.position(pos, scale)
        return spd
# ------------------------------------------------------------------------
    def IMPL02(pos, scale=1.0):
        spd = Speedometer(
                boardFile='images/speedometer2.png', 
                arrowFile='images/speed_arrow2.png', 
                topwardSpeedValueKmh=30, 
                kmh2degScale=90/30,
                minValKmh=0,
                maxValKmh=60
                )
        spd.position(pos, scale)
        return spd
# ------------------------------------------------------------------------
    def IMPL03(pos, scale=1.0):
        spd = Speedometer(
                boardFile='images/speedometer3.png', 
                arrowFile='images/speed_arrow3.png', 
                topwardSpeedValueKmh=90, 
                kmh2degScale=90/60,
                minValKmh=0,
                maxValKmh=63
                )
        spd.position(pos, scale)
        return spd
##########################################################################
class HeartRate (Widget):
    def __init__(self, styleType):
        Widget.__init__(self)
        self.styleType = styleType
        
        self.maxValHR = 250
        self.minValHR = 40
        
        # Fix missing style types
        # WARNING: this is the only place where it's checked. No other 'else's below
        if (self.styleType != 1):
            self.styleType = 1
# ------------------------------------------------------------------------
    def draw(self, img, dataRecord):
        hr = dataRecord['hr']
        if hr < self.minValHR:
            hr = self.minValHR
        if hr > self.maxValHR:
            hr = self.maxValHR
            
        hr = int(hr)
        
        if self.styleType == 1:
            img.paste(self.heart_im, self.pos, self.heart_im)
            draw = ImageDraw.Draw(img) 
            draw.text(self.textPos, str(hr) + ' bpm', font=self.font, fill=(255,0,0,255))
            del draw
        else:
            pass
# ------------------------------------------------------------------------
    def position(self, pos, scale=1.0):
        
        self.pos = pos

        if self.styleType == 1:
            defaultFontSize = 60
            self.pos = (pos[0], int(pos[1] + 5*scale))
            self.textPos = (int((defaultFontSize + 3)*scale + pos[0]), pos[1])
            self.font = ImageFont.truetype('fonts/arial.ttf', int(defaultFontSize*scale))
            self.heart_im = PIL.Image.open('images/heart300.png').resize((int(defaultFontSize*scale), int(defaultFontSize*scale)), resample=PIL.Image.LANCZOS)
            
        else:
            pass
# ------------------------------------------------------------------------
    def clear(self):    
        if self.styleType == 1:
            del self.font
            del self.heart_im
        else:
            pass
        
        Widget.clear(self)
# ------------------------------------------------------------------------
    def IMPL01(pos, scale=1.0):
        hr = HeartRate(
                styleType=1
                )
        hr.position(pos, scale)
        return hr
# ------------------------------------------------------------------------
##########################################################################
