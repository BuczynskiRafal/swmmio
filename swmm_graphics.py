#graphical functions for SWMM files
#import swmmio
import swmm_utils as su
from time import gmtime, strftime
import re
import os
import numpy
from PIL import Image, ImageDraw, ImageFont
from images2gif import writeGif
import glob
import shutil
import math
import datetime
from datetime import timedelta
import pickle


#defined options
nodes_only={'conduitSymb':None, 'width':2048}
conduits_only={'nodeSymb':None, 'width':2048}
bare={'nodeSymb':None, 'conduitSymb':None,'width':2048}
no_parcels = {'parcels':None,'width':2048}
parcels_3hr = {'nodeSymb':None, 'conduitSymb':None, 'parcels':{'threshold':3}, 'width':2048}
parcels_05hr = {'nodeSymb':None, 'conduitSymb':None, 'parcels':{'threshold':0.5}, 'width':2048}

def saveImage(img, model, imgName=None, imgDir=None, antialias=True, open=True, fileExt=".png", verbose=True):
	
	#get the size from the Image object
	imgSize = (img.getbbox()[2], img.getbbox()[3])
	
	#if imgName not specified, define as model name
	if not imgName:
		imgName = model.inp.name
	
	#create the saving location as necessary
	if not imgDir:
		inp = model.inp
		rpt = model.rpt
		standardDir = os.path.join(inp.dir, "img") 
		if not os.path.exists(standardDir):
			#if no directory is specified and none exists at 
			#standard location create a new directory
			os.makedirs(os.path.join(inp.dir, "img"))
		newFile = os.path.join(standardDir, imgName) + fileExt
	else:
		#imDir is specified by user
		if not os.path.exists(imgDir):
			#if directory doesn't exist, create new 
			os.makedirs(imgDir)
		newFile = os.path.join(imgDir, imgName) + fileExt
	
	if verbose: print "saving image to: " + newFile
	
	#shrink for antialiasing niceness (though this blows up the file about 5x)
	if antialias:
		size = (int(imgSize[0]*0.5), int(imgSize[1]*0.5))
		img.thumbnail(size, Image.ANTIALIAS)
	
	img.save(newFile)
	if open:
		os.startfile(newFile)
	
def drawPolygons(imgName=None, width = 1024, feature="Model_Sheds", where="SHEDNAME = 'D68-C1'"):
	#antialias X2
	#width = width*2
	
	polyDict = su.convertPolygonToPixels(feature, targetImgW=width, where=where)
	img = Image.new('RGB', polyDict['imgSize'], (0,3,18))
	draw = ImageDraw.Draw(img) 
	for poly, polyData in polyDict['polygons'].iteritems():
		
		draw.polygon(polyData['draw_coordinates'], fill=(100, 4,150))
		
	saveImage(img, None, imgName, imgDir=r'C:\Users\Adam.Erispaha\Desktop\S Phila SWMM\img')

	
def createFeaturesDict(options={},  bbox=None, shiftRatio=None, width=1024):

	#create dictionary containing draw coordinate data for the given basemap options
	
	#unpack the options
	basemapDicts = basemapOptions.copy() #copy to not mutate the defaults in a session
	basemapDicts.update(options) #update with any changes from user'
	gdb = basemapDicts['gdb']
	features = basemapDicts['features']
	
	import arcpy
	if arcpy.Exists(gdb):
		#if the gdb exists, then we can move forward
		#for feature, data in features.iteritems():
		for featureOps in features:
			feature = featureOps['feature']
			if arcpy.Exists(os.path.join(gdb, feature)):
				#featureDict = data['featureDict']
				#if not featureDict:
				#this check so that we don't repeat this heavy op over an over
				featureDict = su.shape2Pixels(feature, bbox=bbox, targetImgW=width, where=None, cols=featureOps['cols'],
														shiftRatio=shiftRatio, gdb=gdb)
						
						
				featureOps.update({'featureDict':featureDict}) #retain this for later if necessary
				#featureOps['featureDict'].update{featureDict}) #retain this for later if necessary
			else:
				print '{} not found'.format(feature)
	else:
		print '{} not found'.format(gdb) 
		return None		
	
	return basemapDicts
	
def drawParcels(draw, model, options={}, bbox=None, width=1024, shiftRatio=None):
	
	#unpack options
	parcelOps = parcelOptions.copy() #copy to not mutate the defaults in a session
	parcelOps.update(options) #update with any changes from user'
	threshold = parcelOps['threshold']
	
	#get the flooded parcels
	parcels = su.parcelsFlooded(model, threshold = threshold, bbox=bbox, width=width, shiftRatio=shiftRatio)
	
	#img = Image.new('RGB', parcels['imgSize'], su.white)
	#draw = ImageDraw.Draw(img)  
	for parcel, parcelData in parcels['parcels'].iteritems():
		
		fill = su.col2RedGradient(parcelData['avgerage_duration']+0.5, 0, 3)
		#fill = su.greyRedGradient(parcelData['avgerage_duration'], 0, 2)
		draw.polygon(parcelData['draw_coordinates'], fill=fill)
	
	#saveImage(img, None, imgName=model.inp.name + "_parcels", imgDir=r'C:\Users\Adam.Erispaha\Desktop\S Phila SWMM\img')
		
def drawBasemap(draw, img=None, featureDicts=None, options={}, bbox=None, shiftRatio=None, width=1024, xplier=1):
	
	#unpack the options
	#ops = basemapOptions.copy() #copy to not mutate the defaults in a session
	#ops.update(options) #update with any changes from user'
	#gdb = ops['gdb']
	#features = ops['features']
	
	if not featureDicts:
		#generate the dict containing drawable data
		featureDicts = createFeaturesDict(options,  bbox=bbox, shiftRatio=shiftRatio, width=width) #will return None if probs finding data
		
	if featureDicts:
		features = featureDicts['features']
			
		polyDrawCount = 0
		anno_streets = []
		#for feature, data in features.iteritems():
		for feature in features:
			featureDict = feature['featureDict']
			for poly, polyData in featureDict['geometryDicts'].iteritems():
				if polyData['geomType'] == 'polygon':
					draw.polygon(polyData['draw_coordinates'], fill=feature['fill'], outline=feature['outline'])
					polyDrawCount += 1
				
				elif polyData['geomType'] == 'polyline':
					
					draw.line(polyData['draw_coordinates'], fill=feature['fill'], width=feature['width']*xplier)
					if 'ST_NAME' in polyData:
						su.annotateLine(img, polyData, annoKey='ST_NAME', labeled = anno_streets)
						polyDrawCount += 1
				
	
parcelOptions = {
				'threshold':0.083, #hours
				'fill':su.red,
				'outline':su.grey
				}
basemapOptions = {
    'gdb': r'C:\Data\ArcGIS\GDBs\LocalData.gdb',
    'features': [
		#this is an array so we can control the order of basemap layers
        {
            'feature': 'D68_Dissolve',
            'fill': None,
            'outline': su.shed_blue,
            'featureDict': None,
            'cols': ["OBJECTID", "SHAPE@"]
		},
        {
            'feature': 'parcels3',
            'fill': su.lightgrey,
            'outline': None,
            'featureDict': None,
            'cols': ["OBJECTID", "SHAPE@"]
		},
		{
            'feature': 'PhiladelphiaParks',
            'fill': (115, 178, 115),
            'outline': None,
            'featureDict': None,
            'cols': ["OBJECTID", "SHAPE@"]
		},
        {
            'feature': 'HydroPolyTrim',
            'fill': (130, 130, 130),
            'outline': None,
            'featureDict': None,
            'cols': ["OBJECTID", "SHAPE@"]
		},
        {
            'feature': 'Streets_Dissolved5',
            'fill': su.lightgrey,
            'width': 0,
            'fill_anno': su.grey,
            'outline': None,
            'featureDict': None,
            'cols': ["OBJECTID", "SHAPE@", "ST_NAME"]
		}
      ],
}
defaultDrawOptions = {
				'width':1024,
				'nodeSymb':'flood',
				'conduitSymb':'stress',
				'basemap':basemapOptions,
				'parcels':parcelOptions,
				'bg':su.white,
				'xplier':1,
				'focusConduits':[],
				'traceUpNodes':[],
				'traceDnNodes':[],
				'fps':7.5,
				'title':None
			}
#def drawModel (imgName, model, width = 1024, xplier = 1, bbox = None, proposedID=None, 
#						conduitSymb="flow", nodeSymb='flood', basemap=True, bg = su.white):
def drawModel (model, imgName=None, bbox=None, options={}):	
	
	#unpack the options
	ops = defaultDrawOptions.copy() #copy to not mutate the defaults in a session
	ops.update(options) #update with any changes from user'
	width = 		ops['width']
	nodeSymb = 		ops['nodeSymb']
	conduitSymb = 	ops['conduitSymb']
	basemap = 		ops['basemap']
	parcels = 		ops['parcels']
	bg = 			ops['bg']
	xplier = 		ops['xplier']
	focusConduits = [] #=	ops['focusConduits']
	traceUpNodes =	ops['traceUpNodes']
	traceDnNodes =	ops['traceDnNodes']
	
	print traceUpNodes
	print traceDnNodes
	for node in traceUpNodes:
		#return list of elements upstream of node
		focusConduits += su.traceFromNode(model, node, mode='up')['conduits']
		
	for node in traceDnNodes:
		#return list of elements downstream of node
		focusConduits += su.traceFromNode(model, node, mode='down')['conduits']
	
	#antialias X2
	xplier *= width/1024 #scale the symbology sizes
	width = width*2
	
	
	#parse out the main objects of this model
	inp = model.inp
	rpt = model.rpt
	
	#organize relavant data from SWMM files
	conduitData = model.organizeConduitData(bbox) #dictionary of overall model data, dimension, and the conduit dicts
	conduitDicts = conduitData['conduitDictionaries']
	pixelData = su.convertCoordinatesToPixels(conduitDicts, targetImgW=width, bbox=bbox)
	shiftRatio = pixelData['shiftRatio']
	imgSize = pixelData['imgSize']
	if not bbox:
		bbox = pixelData['boundingBox'] #this is the box tightly wrapping all conduits, will be <= the user provided bbox
	
	#node data 
	nodeData = model.organizeNodeData(bbox)
	nodeDicts = nodeData['nodeDictionaries']
	su.convertCoordinatesToPixels(nodeDicts, targetImgW=width, bbox=bbox)
	
	
	
	img = Image.new('RGB', imgSize, bg)
	draw = ImageDraw.Draw(img)
	
	
	if basemap:
		drawBasemap(draw, img=img, options=basemap, width=width, bbox=bbox, shiftRatio=shiftRatio, xplier = xplier)
	if parcels:
		drawParcels(draw, model, options=parcels, width=width, bbox=bbox, shiftRatio=shiftRatio)
	
		
	drawCount = 0
	
	#DRAW THE CONDUITS
	if conduitSymb:
		for conduit, coordPairDict in conduitDicts.iteritems():
			
			if 'maxflow' in coordPairDict: 
			#try:
				su.drawConduit(conduit, coordPairDict, draw, rpt=rpt, xplier = xplier, type=conduitSymb, highlighted=focusConduits)	
				drawCount += 1
			#except:
			#	pass #rdii and others that don't have flow data fail 
		
	
	#DRAW THE NODES
	if nodeSymb:
		for node, nodeDict in nodeDicts.iteritems():
			if 'floodDuration' in nodeDict: #this prevents draws if no flow is supplied (RDII and such)
				su.drawNode(node, nodeDict, draw, rpt, dTime=None, xplier=xplier, type=nodeSymb)
				drawCount += 1
	
	#if conduitDrawCount > 0 and conduitDrawCount % 2000 == 0: print str(conduitDrawCount) + " pipes processed "
	print "drawCount = " + str(drawCount)
	
	su.drawAnnotation (draw, inp, rpt, imgWidth=width, title=None, symbologyType=conduitSymb, fill=su.black, xplier=xplier)
	del draw, ops
	
	#SAVE IMAGE TO DISK
	saveImage(img, model, imgName)
	

def animateModel(model, imgName=None, startDtime=None, endDtime=None, bbox=None, options={}):	
	
	#unpack the options
	ops = defaultDrawOptions.copy()
	ops.update(options) #update with any changes from user'
	width = 		ops['width']
	nodeSymb = 		ops['nodeSymb']
	conduitSymb = 	ops['conduitSymb']
	basemap = 		ops['basemap']
	bg = 			ops['bg']
	xplier = 		ops['xplier']
	fps =			ops['fps']
	
	#for antialiasing, double size for now
	xplier *= width/1024 #scale the symbology sizes
	width = width*2
	
	#parse out the main object of this model
	inp = model.inp
	rpt = model.rpt
	
	#organize relavant data from SWMM files
	conduitData = model.organizeConduitData(bbox) #dictionary of overall model data, dimension, and the conduit dicts
	conduitDicts = conduitData['conduitDictionaries']
	pixelData = su.convertCoordinatesToPixels(conduitDicts, targetImgW=width, bbox=bbox)
	shiftRatio = pixelData['shiftRatio']
	imgSize = pixelData['imgSize']
	#node data 
	nodeData = model.organizeNodeData(bbox)
	nodeDicts = nodeData['nodeDictionaries']
	su.convertCoordinatesToPixels(nodeDicts, targetImgW=width, bbox=bbox)
	
	#grab start and end simulation time if no range provided -> this will be huge if you're not careful!
	if not startDtime: startDtime = rpt.simulationStart
	if not endDtime: endDtime = rpt.simulationEnd
	
	#make sure dates are valid (within range)
	simStartDT = datetime.datetime.strptime(rpt.simulationStart, "%b-%d-%Y %H:%M:%S") #lower bound of time
	simEndDT = datetime.datetime.strptime(rpt.simulationEnd, "%b-%d-%Y %H:%M:%S") #upper bound of time
	if startDtime and endDtime:
		userStartDT = 	datetime.datetime.strptime(startDtime, "%b-%d-%Y %H:%M:%S")
		userEndDT = 	datetime.datetime.strptime(endDtime, "%b-%d-%Y %H:%M:%S")
		timeStepMod = userStartDT.minute % rpt.timeStepMin
		if userStartDT < simStartDT or userEndDT > simEndDT or timeStepMod != 0 or userEndDT < userStartDT:
			#user has entered fault date times either by not being within the 
			#availble data in the rpt or by starting at something that doesn't fit the timestep
			print "PROBLEM WITH DATETIME ENTERED. Make sure it fits within data and start time rest on factor of timestep in minutes."
			print "userStartDT = ", userStartDT, "\nuserEndDT = ", userEndDT, "\nsimStartDT = ", simStartDT, "\nsimEndDT = ", simEndDT, "\nTIMESTEP = ", rpt.timeStepMin
			return None
	
	currentT = datetime.datetime.strptime(startDtime, "%b-%d-%Y %H:%M:%S") #SWMM dtime format needed 
	endDtime = datetime.datetime.strptime(endDtime, "%b-%d-%Y %H:%M:%S") #SWMM dtime format needed 
	delta = timedelta(minutes=rpt.timeStepMin) #SWMM reporting time step (or step to animate with)
	
	
	#use or create working dir 
	if not os.path.exists( os.path.join(inp.dir, "img") ):
		os.makedirs(os.path.join(inp.dir, "img"))
	imgDir = os.path.join(inp.dir, "img") 
	
	byteLocDictionaryFName = os.path.join(imgDir, inp.name) + "_rpt_key.txt"
	if not os.path.isfile(byteLocDictionaryFName):
		
		#this is a heavy operation, allow a few minutes
		print "generating byte dictionary..."
		#conduitByteLocationDict = rpt.createByteLocDict("Link Results")
		rpt.createByteLocDict("Link Results")
		rpt.createByteLocDict("Node Results")
		
		#save dict to disk
		dictSaveFile =  open (byteLocDictionaryFName, 'w')
		pickle.dump(rpt.elementByteLocations, dictSaveFile)
		dictSaveFile.close()
	
	else:
		print "loading byte dict"
		rpt.elementByteLocations = pickle.load( open(byteLocDictionaryFName, 'r') ) 
		#rpt.byteLocDict = conduitByteLocationDict
		
	print "Started Drawing at " + strftime("%b-%d-%Y %H:%M:%S")
	log = "Started Drawing at " + strftime("%b-%d-%Y %H:%M:%S") + "\n\nErrors:\n\n"
	drawCount = 0
	conduitErrorCount = 0
	print "conduitSymb = " + conduitSymb
	font = ImageFont.truetype(su.fontFile, 30)
	basemapFeatureDicts = createFeaturesDict(options=basemap,  bbox=bbox, shiftRatio=shiftRatio, width=width) #will be populated after first frame is produced
	while currentT <= endDtime:
		
		img = Image.new('RGB', imgSize, bg) 
		draw = ImageDraw.Draw(img) 
		currentTstr = currentT.strftime("%b-%d-%Y %H:%M:%S").upper()
		#print 'time =', currentTstr
		
		#DRAW THE BASEMAP
		if basemap:
			drawBasemap(draw, img=img, options=basemap, width=width, bbox=bbox, featureDicts=basemapFeatureDicts, xplier = xplier)
			
		#DRAW THE CONDUITS
		if conduitSymb:
			for conduit, coordPairDict in conduitDicts.iteritems():
				#coordPair = coordPairDict['coordinates']
				if 'maxflow' in coordPairDict: #this prevents draws if no flow is supplied (RDII and such)
					
					su.drawConduit(conduit, coordPairDict, draw, rpt=rpt, dTime = currentTstr, 
									xplier = xplier, type=conduitSymb)
					
					drawCount += 1
					
				if drawCount > 0 and drawCount % 2000 == 0: print str(drawCount) + " pipes drawn - simulation time = " + currentTstr
		
		#DRAW THE NODES
		if nodeSymb:
			for node, nodeDict in nodeDicts.iteritems():
				if 'floodDuration' in nodeDict: #this prevents draws if no flow is supplied (RDII and such)
					su.drawNode(node, nodeDict, draw, rpt, dTime=currentTstr, type=nodeSymb, xplier=xplier)
					drawCount += 1
					
		
		#DRAW THE ANNOTATION
		dtime = currentT.strftime("%b%d%Y_%H%M").upper()
		su.drawAnnotation (draw, inp, rpt, imgWidth=width, title=None, currentTstr = currentTstr, fill=su.black)
		currentT += delta
		del draw
		
		
		#shrink for antialiasing niceness (though this blows up the file about 5x)
		tempImgDir = os.path.join(imgDir, "temp_frames")
		saveImage(img, model, dtime, imgDir=tempImgDir, open=False, verbose=False)

	#WRITE THE GIF 
	frames = []
	for image in glob.glob1(tempImgDir, "*.png"):
		imgPath = os.path.join(tempImgDir, image)
		frames.append(Image.open(imgPath))
	
	print "building gif with " + str(len(glob.glob1(tempImgDir, "*.png"))) + " frames..."
	if not imgName: imgName = inp.name
	gifFile = os.path.join(imgDir, imgName) + ".gif" 
	frameDuration = 1.0 / float(fps)
	writeGif(gifFile, frames, duration=frameDuration)
	
	shutil.rmtree(tempImgDir) #delete temporary frames directory after succesful GIF
	
	log += "Completed drawing at " + strftime("%Y%m%d %H:%M:%S") 
	with open(os.path.join(imgDir, "log.txt"), 'w') as logFile:
		logFile.write(log)
	
	print "Draw Count =" + str(drawCount)
	print "Video saved to:\n\t" + gifFile
	
	os.startfile(gifFile)#this doesn't seem to work
	
def drawProfile (model, imgName=None, imgDir=None, width = 1024, height=512, drawSizeMultiplier = .01, 
				bgroundColor=(0,3,18), bbox = None, conduitSubset = None, extraData=None):
		
	
	width = width*2
	height = height*2
	
	#match the coordinates for each conduit
	processed = self.organizeConduitData(rpt = rpt, conduitSubset = conduitSubset, extraData = extraData, findOrder=True)
	
	conduiteElevationDicts = processed['conduitDictionaries']
	modelSize = processed['boundingBox']
	minEl = processed['minEl']
	maxEl = processed['maxEl']
	reachLength = processed['reachLength']
	startingConduitID = processed['startingConduit'][0]
	
	
	#transform 
	profileHeight = maxEl - minEl
	
	shiftRatioX = width / reachLength # to scale down from coordinate to pixels
	shiftRatioY = height / profileHeight # to scale down from coordinate to pixels
	
	print height, " x " , width
	print "minEl = ",  minEl
	print "maxEl = ",  maxEl
	print "shiftRatioY = ",  shiftRatioY
	print "shiftRatioX = ",  shiftRatioX
	print 'reachLength = ', reachLength
	
	for conduitID, data in conduiteElevationDicts.iteritems():

		#print data
		drawLength = round(data['length'] * shiftRatioX, 5)
		#need to shirt the x n y components of the length 
		
		inv1 =		round((maxEl - data['upstreamEl']) * shiftRatioY, 5) #subtract from height because PIL origin is in top right
		inv2 = 		round((maxEl - data['downstreamEl'])  * shiftRatioY, 5)  #subtract from height because PIL origin is in top right
		HGL1 = 		round((maxEl - data['maxHGLUpstream']) * shiftRatioY, 5)
		HGL2 = 		round((maxEl - data['maxHGLDownstream']) * shiftRatioY, 5)
		upFloodEl = None
		dnFloodEl = None
		if extraData and data['upFloodEl'] and data['dnFloodEl']:
			upFloodEl = round((data['upFloodEl']) * shiftRatioY, 5)
			dnFloodEl = round((data['dnFloodEl']) * shiftRatioY, 5)
			
		tranformedDictItems = {'drawLength':drawLength, 'inv1':inv1, 'inv2':inv2, 'HGL1':HGL1, 'HGL2':HGL2, 'upFloodEl':upFloodEl, 'dnFloodEl':dnFloodEl}
			
		
		#coordPairDict.update(tranformedDictItems)
		data.update(tranformedDictItems)
	
	
	print "new size X2 = " , modelSize
	print "startingConduitID = " + startingConduitID
	img = Image.new('RGB', (width, height), bgroundColor) 
	draw = ImageDraw.Draw(img) 
	
	#draw conduits from the starting pipe
	conduit = conduiteElevationDicts[startingConduitID]
	#print conduit
	x1 = 0
	terminalFound = False
	
	
	while not terminalFound:
		
		#loop through conduits, switching to each conduit via the "downID"
		#stop when the t
		length = conduit['drawLength']
		inv1 = conduit['inv1']
		inv2 = conduit['inv2']
		HGL1 = conduit['HGL1']
		HGL2 = conduit['HGL2']
		upFloodEl = conduit['upFloodEl']
		dnFloodEl = conduit['dnFloodEl']
		
		geom1 = float(conduit['geom1']) * shiftRatioY
		x2 = length + x1 #su.getX2(inv1, inv2, length, x1)
		invCoordPair = [(x1, inv1), (x2, inv2)] #coordPairs for the pipe invert
		crwnCoordPair = [(x1, inv1-geom1), (x2, inv2-geom1)] #coordPairs for the pipe crown
		HGLCoordPair = [(x1, HGL1), (x2, HGL2)] #coordPairs for the HGL
		#print invCoordPair
		draw.line(invCoordPair, fill = (200, 200, 200), width = 2)
		draw.line(crwnCoordPair, fill = (200, 200, 200), width = 2)
		draw.line(HGLCoordPair, fill = (10, 120, 250), width = 2)
		
		if upFloodEl and dnFloodEl:
			floodElCoordPair = [(x1, inv1-upFloodEl), (x2, inv2-dnFloodEl)] #coordPairs for the pipe crown
			draw.line(floodElCoordPair, fill = (30, 250, 130), width = 2)
		
			
		nextConduitID = conduit['downID']
		if nextConduitID:
			#advance to next reach downstream, if a downID exists
			x1 = x2 #increment the x starting point for the next conduit
			#print str(conduit) + " to " + str([conduit['downID']])
			conduit = conduiteElevationDicts[nextConduitID]
		else: 
			terminalFound = True
			#print "terminal" + str(conduit)

					
	del draw
			
	newFile = os.path.join(imgDir, imgName) + ".png"
	print newFile
	
	
	#shrink for antialiasing niceness (though this blows up the file about 5x)
	size = (int(width*0.5), int(height*0.5))
	img.thumbnail(size, Image.ANTIALIAS)
	
	img.save(newFile)
	os.startfile(newFile)
	#return conduiteElevationDictss