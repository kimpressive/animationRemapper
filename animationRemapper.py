#Animation remapper
import pymel.core as pm
import json
import time
from maya.mel import eval as meleval


class AnimationRemapper():
    """
    Run script with:
        import animationRemapper;
        animationRemapper.AnimationRemapper()

    How to use:
    Select some objects with animation on them. Then press Start.
    Now slide the timeslider around and a scriptNode will record the time when you dragged it.
    Pull the slider back to 1 to reset.
    Press Stop to change the keyframes.
    """
    _mapKeyFrameList    = [] #Record keyframes
    _mapTimeList        = [] #Recrod timestamps
    _selectedObjects    = []
    _startTime = pm.playbackOptions(q=1, min=1)
    _endTime = pm.playbackOptions(q=1, max=1)
    _startRecordingTime = time.time()
    _lastKey            = _startTime
    _snapKeys           = False

    def __init__(self, snapKeys=True):
        #Makes sure that it doesnt create any duplicates
        self.fps = meleval("currentTimeUnitToFPS")
        try:
            self.scriptNode = pm.PyNode("AnimationRemapperScriptNode")
            self.scriptNode.before.set("pass")
        except:
            pm.scriptNode(n="AnimationRemapperScriptNode", stp="python", st=7, bs="pass")
            self.scriptNode = pm.PyNode("AnimationRemapperScriptNode")

        if snapKeys:
            self.snapKeys()

        self.createUI()


    def snapKeys(self):
        AnimationRemapper._snapKeys = True

    ######################
    #       UI buttons
    ######################
    def createUI(self):
        if pm.window("AnimationRemapperUI", exists=1):
            pm.deleteUI("AnimationRemapperUI")

        win = pm.window("AnimationRemapperUI", h=100, w=100)
        layout = pm.columnLayout()
        self.startStopBtn = pm.button(label="Start", parent=layout, command=self.stopStartBtnPressed, h=100, w=100)
        self.selectionBtn = pm.button(label="Get selection", parent=layout, command=self.selectionBtnPressed, h=100, w=100)
        pm.showWindow()

    def selectionBtnPressed(self, *args):
        self._selectedObjects = pm.selected()

    def stopStartBtnPressed(self, *args):
        ######   Start the Script
        if self.startStopBtn.getLabel() == "Start":
            self.startStopBtn.setLabel("Stop")
            self.startRecording()

        else:
            self.startStopBtn.setLabel("Start")
            self.stopRecording()

    ######################
    # Recording functionality
    ######################
    def startRecording(self):
        if not self._selectedObjects:
            self._selectedObjects = pm.selected()

        self.fps = meleval("currentTimeUnitToFPS")
        pm.play(state=False)
        
        #update "class variables" variables
        AnimationRemapper._startRecordingTime = time.time()
        AnimationRemapper._startTime = pm.playbackOptions(q=1, min=1)
        AnimationRemapper._endTime = pm.playbackOptions(q=1, max=1)
        AnimationRemapper._mapKeyFrameList  = []
        AnimationRemapper._mapTimeList      = []

        #Start the scriptNode and set the currentTime to the start of the timerange
        module = __name__
        #Activate the scriptNode
        self.scriptNode.before.set("import {0}; {0}.scriptNodeCall()".format(module))
        pm.currentTime(AnimationRemapper._startTime) #Setting the time to start time resets the dict

    def stopRecording(self):
        self.scriptNode.before.set("pass")      #Inactivates the scriptNode
        
        if len(AnimationRemapper._mapKeyFrameList) < 2:
            print "Stopped script. No recorded keys"
            return

        #Converts the time list to delta time in keyframes
        self._convertTimeList()
        
        #Print for debugging
        lastKeyFrame = AnimationRemapper._mapKeyFrameList[-1] #
        lastTime = AnimationRemapper._mapTimeList[-1] #convert time to keyframe
        
        lastKey = max([pm.findKeyframe(selObj, w="last") for selObj in self._selectedObjects])
        
        moveVal = lastTime - lastKeyFrame

        #Set timerange options
        if lastTime > pm.playbackOptions(q=1, max=True):
            pm.playbackOptions(e=1, max=lastTime)

        #If moveVal is greater than zero move the untouched keyframes further away before we remap
        if moveVal > 0:
            self.moveUnusedKeyframes(lastKeyFrame, lastKey, moveVal)

        #Do the magic
        self.remapKeys()

        #If moveVal is less than zero move the untouched keyframes closer to the remapped animation
        #(if you only remapped parts of the animation)
        if moveVal < 0:
            self.moveUnusedKeyframes(lastKeyFrame, lastKey, moveVal)

    ######################
    # Remapping functionality
    ######################
    def _convertTimeList(self):
        startRecTime = AnimationRemapper._startRecordingTime
        l = [(t - startRecTime) * self.fps for t in AnimationRemapper._mapTimeList]
        AnimationRemapper._mapTimeList = l


    def _createFilledTimeLists(self):
        """
            Since Maya often doesnt have time to record every keyframe. Especially in heavt scenes
            this creates lists that fill in the blanks.
        """
        def removeDupes(l):
            nl = []
            for x in l:
                if not x in nl:
                    nl.append(x)
            return nl

        kl = AnimationRemapper._mapKeyFrameList
        tl = AnimationRemapper._mapTimeList

        filledKeyList = []
        filledTimeList = []

        for i in range(len(kl)):
            try:
                k1, k2 = kl[i], kl[i+1]
                t1, t2 = tl[i], tl[i+1]
            except:
                break
            kList = range(int(k1), int(k2+1))
            tList = []
            for k in kList:
                timeBlend = pm.util.mathutils.setRange(k, k1, k2, t1, t2)
                tList.append(timeBlend)
            filledKeyList.extend(kList)
            filledTimeList.extend(tList)

        filledKeyList = removeDupes(filledKeyList)
        filledTimeList = removeDupes(filledTimeList)
        
        #for i, z in zip( filledKeyList, filledTimeList):
        #    print i, z

        return filledKeyList, filledTimeList


    def remapKeys(self):
        kList, tList = self._createFilledTimeLists()
        if (round(tList[0])-1) < AnimationRemapper._startTime:
            print "Youre moving too fast!"
            return 

        kList.reverse() #
        tList.reverse() # Reverse the lists so you cant accidentaly place keys on top of other keys

        lastSnappedKey = 0.0
        for key, timeKey in zip(kList, tList):
            #print key, timeKey
            
            if self._snapKeys:
                timeKey = round(timeKey, 0)
                if timeKey == lastSnappedKey:
                    timeKey = timeKey-1
                lastSnappedKey = timeKey

            for selectedObject in self._selectedObjects:
                r = pm.keyframe(selectedObject, e=1, t=(key,key+1), tc=timeKey)
                if r == 10:
                    print key, timeKey
        
        return 




        for recordedFrame, recordTime in a:
            newFrame = round(recordTime*self.fps, 2)
            int_recordedFrame = int(float(recordedFrame))      #Converts from String to Int
            
            try:
                for selectedObject in self._selectedObjects:
                    
                    r = pm.keyframe(selectedObject, e=1, t=(int_recordedFrame,int_recordedFrame+1), tc=newFrame)
                    if r == 10.0:
                        print "recordedFrame :", int_recordedFrame, "newFrame:", newFrame
                del AnimationRemapper._remapperDict[recordedFrame]
            except:
                print "Error at keyframing ", int_recordedFrame, newFrame
                pass #If the pm.keyframe command fails then we shouldnt empty the dict

        if AnimationRemapper._remapperDict:
            #Run the function recursively until the dictionary is empty
            return self._moveKeys
        else:
            return True


    #######
    # MISC
    ######
    def dictReverseSorter(self, adict):
        keys = sorted([float(key) for key in adict.keys()], reverse=True)
        keys = [str(key) for key in keys]
        return keys

    def moveUnusedKeyframes(self, lastDictKey, lastKey, moveVal):
        for selObj in self._selectedObjects:
            pm.keyframe(selObj, e=1, relative=1, t=(lastDictKey, lastKey), tc=(moveVal))


def scriptNodeCall():
    #This is called by the script node to update the dict
    ct = meleval( "currentTime -q" )
    if ct > AnimationRemapper._lastKey: 
        AnimationRemapper._lastKey = ct
        AnimationRemapper._mapKeyFrameList.append( ct )
        AnimationRemapper._mapTimeList.append( time.time() )

    if ct == AnimationRemapper._startTime:
        AnimationRemapper._lastKey = AnimationRemapper._startTime
        AnimationRemapper._mapKeyFrameList    = [] #Reset
        AnimationRemapper._mapTimeList        = [] #Reset
        AnimationRemapper._startRecordingTime = time.time()
        AnimationRemapper._remapperDict = {}
        
    
