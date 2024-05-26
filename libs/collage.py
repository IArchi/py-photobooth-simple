import shlex
import subprocess
from kivy.logger import Logger

class Collage:

    @staticmethod
    def create_collage(output_name='collage.jpg', photos=[], dual_print=False):
        Logger.info('Collage: create_collage().')
        # cmd = 'montage'
        # if dual_print:
        #     cmd = cmd + " -tile 2x{}".format(len(photos))
        #     for i in range(0, len(photos)):
        #         cmd = cmd + ' ' + photos[i]
        #         cmd = cmd + ' ' + photos[i]
        #     cmd = cmd + ' -geometry +30+30 {}'.format(output_name)
        # else:
        #     cmd = cmd + "-tile 1x{} ".format(len(photos))
        #     for i in range(0, len(photos)):
        #         cmd = cmd + ' ' + photos[i]
        #     cmd = cmd + '-geometry +30+30 {}'.format(output_name)
        #
        # Logger.info('Collage: Command is %s', cmd)
        # return subprocess.Popen(shlex.split(cmd))
        tr = TemplateReader(templateDir, 'template.xml')
        ip = ImageProcessor(tr)

        result = ip.processImages(photos)
        result.save(output_name)

# TODO Create template : https://github.com/samckittrick/Qt-Py-Photobooth

"""Module for processing and managing Photo Templates
By: Scott McKittrick

Photo templates are packages of files that describe how many photos
should be taken by the photo booth and how those photos should be arranged.
They also support background images and foreground overlays.

The Photo template package is made up of an XML file called "template.xml"
and any other resources referenced in the XML. Photo templates are stored in
their own directory called "Templates" and each template is pacakged in it's
own directory with it's name as the directory name. Ex. Template structure.
---------------------------------
|Configurable Photo template Dir|
--------------------------------
|                             |
-------------                ----------------
| Template 1|                | Template 2   |
-------------                ----------------
|        |________,           |             |_______,
--------------   --------     ----------------     ---------
template.xml |   |img 1 |     | template.xml |     | img 2 |
--------------   --------     ----------------     ---------

By: Scott McKittrick

Dependencies:
python3-lxml - Python bindings for libxml2 and libxslt libraries

Classes Contatined:
TemplateReader - Class that parses and contains the data in a template.xml file.
ImageProcessor - Class that takes a template and provides an interface to use it to create final images.
TemplateError  - Exception Class representing errors reading the template file.
"""
import os
from lxml import etree
from PIL import Image

##############################################################
# TemplateReader Class                                      #
##############################################################
class TemplateReader:
    """ Class that parses and contains the data in a template.xml file

    This class takes a directory name and searches for a template.xml file. If one is found, it will validate and read the file.

    """
    TemplateXMLFilename = "template.xml"
    TemplateXSD = "PhotoTemplate.xsd"
    NS = "{http://www.scottmckittrick.com/schema/PiBooth/PhotoTemplate}"

    #----------------------------------------------------------------------
    def __init__(self, dirname, filename):
        """Template reader constructor

        Parses a template package and stores the resultant data for access.
        Throws TemplateError when it has problems parsing a template package."""
        self.TemplateDir = dirname
        self.TemplateFilename = self.TemplateDir + os.path.sep + filename
        #Initialize data members
        self.templateName = None
        self.description = None
        self.author = None
        self.previewImageFilename = None
        self.backgroundColor = None
        self.height = None
        self.width = None
        self.backgroundPhoto = None
        self.foregroundPhoto = None
        self.photoList = list()

        try:
            print("Loading Template: " + self.TemplateFilename)

            #load the template xml
            self.template_xml = etree.parse(self.TemplateFilename)

            #validate agains the XSD file
            print("Validating template file for " + self.TemplateFilename)
            if(self.__validateFile() != True):
                raise TemplateError("Error: XML Validation failed. ")
            else:
                print("Validation succeeded!")

            #Begin parsing the xml for data
            self.__parseFile()

        except OSError as err:
            print("Error reading Template: " + str(err))
            raise TemplateError("Error reading template files.")
        except etree.XMLSyntaxError as err:
            print("Error reading Template: " + str(err))
            raise TemplateError("Error parsing template xml")

    #--------------------------------------------------------------------------------
    def __validateFile(self):
        """Validates the file against a specific XML Schema Definition document. """

        xml_schema_doc = etree.parse(TemplateReader.TemplateXSD)
        xmlSchema = etree.XMLSchema(xml_schema_doc)

        return xmlSchema.validate(self.template_xml)

    #--------------------------------------------------------------------------------
    def __parseFile(self):
        """Parses the template.xml file and stores the data in the object"""
        root = self.template_xml.getroot()

        self.templateName = root.find(self.NS+"name").text

        descriptionElem = root.find(self.NS+"description")
        if(descriptionElem is not None):
            self.description = descriptionElem.text

        authorElem = root.find(self.NS+"author")
        if(authorElem is not None):
            self.author = authorElem.text

        previewImageElem = root.find(self.NS+"previewImage")
        if(previewImageElem is not None):
            self.previewImageFilename = previewImageElem.get("src")

        canvas = root.find(self.NS+"canvas")
        self.__parseCanvas(canvas)

    #--------------------------------------------------------------------------------
    def __parseCanvas(self, canvas):
        """Parses the canvas object and it's contents"""
        backgroundColorAttr = canvas.get("backgroundColor")
        if(backgroundColorAttr is not None):
            self.backgroundColor = backgroundColorAttr

        self.height = int(canvas.get("height"))
        self.width = int(canvas.get("width"))

        backgroundPhotoElem = canvas.find(self.NS+"backgroundPhoto")
        if(backgroundPhotoElem is not None):
            self.backgroundPhoto = self.TemplateDir + os.path.sep + backgroundPhotoElem.get("src")

        foregroundPhotoElem = canvas.find(self.NS+"foregroundPhoto")
        if(foregroundPhotoElem is not None):
            self.foregroundPhoto = self.TemplateDir + os.path.sep + foregroundPhotoElem.get("src")

        photoList = canvas.find(self.NS+"photos")
        self.__parsePhotoList(photoList)

    #---------------------------------------------------------------------------------
    def __parsePhotoList(self, photoList):
        """Parses the photo list object and it's contents"""
        self.photoList = list()
        for photoSpec in photoList.getchildren():
            height = int(photoSpec.get("height"))
            width = int(photoSpec.get("width"))
            x = int(photoSpec.get("x"))
            y = int(photoSpec.get("y"))
            if(photoSpec.get("rotation") is None):
                rot = 0
            else:
                rot = int(photoSpec.get("rotation"))

            photoSpecTuple = {'x': x, 'y': y, 'width': width, 'height': height, 'rotation': rot}
            self.photoList.append(photoSpecTuple)

    #-----------------------------------------------------------------------#
    def getTemplatePreviewPath(self):
        """Returns the path to the preview image file."""
        if(self.previewImageFilename != None):
            return self.TemplateDir + os.path.sep + self.previewImageFilename
        else:
            return None

    #-----------------------------------------------------------------------#
    def getMaxImageSize(self):
        """Get the size of the largest image. Currently assumes that all images will be the same aspect ratio"""
        maxSize = (0,0)
        for spec in self.photoList:
            if(spec['width'] > maxSize[0]):
                maxSize = (spec['width'], spec['height'])
        return maxSize

#################################################################
# ImageProcessor                                                #
#################################################################
class ImageProcessor:
    """Contains a template object and provides an interface to process image sets based on the template. The template within it cannot be changed. Instead, simply create a new ImageProcessor object with a new template."""

    #------------------------------------------------------------------------#
    def __init__(self, template):
        """Constructor takes TemplateReader object. """
        self.template = template

    #-----------------------------------------------------------------------#
    def processImages(self, imageList):
        """Takes a list of images and processes them according to the contained template. Returns a PIL Image object"""

        # Create the initial canvas
        canvasSize = (self.template.width, self.template.height)
        if(self.template.backgroundColor != None):
            canvasColor = self.hex_to_rgb(self.template.backgroundColor)
        else:
            canvasColor = (0,0,0,0)
        mImg = Image.new("RGB", canvasSize, canvasColor)

        #Paste in the background image if there is one.
        if(self.template.backgroundPhoto != None):
            bgImg = Image.open(self.template.backgroundPhoto)
            mImg.paste(bgImg, (0, 0))

        #For each photo resize, rotate and paste.
        #Note the image is resized before rotation. However, since the
        #   coordinate system does not allow for rotated rectangles the
        #   x and y coordinates now represent the upper left corner of
        #   the new bounding box.
        #Note: The rotation value is the degrees to rotate counter clockwise
        for i in range(0, len(self.template.photoList)):
            photoSpec = self.template.photoList[i]
            takenImg = imageList[i].convert("RGBA")
            takenImg.thumbnail((photoSpec['width'], photoSpec['height']), Image.ANTIALIAS)
            if(photoSpec['rotation'] != 0):
                tmp = takenImg.rotate(photoSpec['rotation'], Image.BILINEAR, 1)
                takenImg = tmp
            mImg.paste(takenImg, (photoSpec['x'], photoSpec['y']), takenImg)

        #paste the overlay.
        if(self.template.foregroundPhoto != None):
            fgImg = Image.open(self.template.foregroundPhoto)
            mImg.paste(fgImg, (0,0), fgImg)

        return mImg

    #-----------------------------------------------------------------------#
    def hex_to_rgb(self,value):
        value = value.lstrip('#')
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

#################################################################
# TemplateError                                                 #
#################################################################
class TemplateError(Exception):
    """Thrown for errors parsing templates."""
    pass
