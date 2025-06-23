script_imp_listener = r'''
#@ boolean mode
from ij import IJ
from ij import WindowManager
from ij import ImagePlus
from java.awt import Frame
import ij.ImageListener as ImageListener

class MinimizingImageListener(ImageListener):
    def imageOpened(self, imp):
        IJ.run("Tile")
        self.minimize_window(imp.getWindow())
    
    def imageClosed(self, imp):
        pass
    
    def imageUpdated(self, imp):
        self.minimize_window(imp.getWindow())
    
    @staticmethod
    def minimize_window(window):
        if window is None:
            return
        window.setLocationAndSize(0, 0, window.MIN_WIDTH, window.MIN_HEIGHT)
        window.setState(Frame.ICONIFIED)
            
if mode == True:
    listener = MinimizingImageListener()
    ImagePlus.addImageListener(listener)
else:
    listenerList = ImagePlus.getListeners()
    toRemoveList = []
    for listener in listenerList:
        toRemoveList.append(listener)
    for listener in toRemoveList:
        ImagePlus.removeImageListener(listener)
'''