from typing import Callable
import logging

from PIL import Image, ImageFilter, ImageEnhance
from PIL.ImageFilter import Filter
from PIL import ImageOps

import numpy as np
from cv2 import dnn_superres, cvtColor, fastNlMeansDenoisingColored, COLOR_RGB2BGR, COLOR_BGR2RGB

def _ManipulateImage(inputImage: Image.Image, filter: Filter | Callable[[], Filter]) -> Image.Image:
    # Manipulate the image
    return inputImage.filter(filter)

def Sharpen(inputImage: Image.Image) -> Image.Image:
    # Sharpen the image
    return _ManipulateImage(inputImage, ImageFilter.SHARPEN)

def Blur(inputImage: Image.Image) -> Image.Image:
    # Blur the image
    return _ManipulateImage(inputImage, ImageFilter.BLUR)

def Contour(inputImage: Image.Image) -> Image.Image:
    # Contour the image
    return _ManipulateImage(inputImage, ImageFilter.CONTOUR)

def Detail(inputImage: Image.Image) -> Image.Image:
    # Detail the image
    return _ManipulateImage(inputImage, ImageFilter.DETAIL)

def EdgeEnhance(inputImage: Image.Image) -> Image.Image:
    # Edge enhance the image
    return _ManipulateImage(inputImage, ImageFilter.EDGE_ENHANCE)

def Emboss(inputImage: Image.Image) -> Image.Image:
    # Emboss the image
    return _ManipulateImage(inputImage, ImageFilter.EMBOSS)

def FindEdges(inputImage: Image.Image) -> Image.Image:
    # Find Edges the image
    return _ManipulateImage(inputImage, ImageFilter.FIND_EDGES)

def Smooth(inputImage: Image.Image) -> Image.Image:
    # Smooth the image
    return _ManipulateImage(inputImage, ImageFilter.SMOOTH)

def UnsharpMask(inputImage: Image.Image) -> Image.Image:
    # Sharpen the image using an unsharp mask
    return _ManipulateImage(inputImage, ImageFilter.UnsharpMask)

def AutoContrast(inputImage: Image.Image) -> Image.Image:
    # Return the autocongtrasted image
    return ImageOps.autocontrast(inputImage)

def Colour(inputImage: Image.Image, factor: float) -> Image.Image:
    # Create the enhancement tool
    enhance = ImageEnhance.Color(inputImage)

    # Manipulate the image
    return enhance.enhance(factor)

def Contrast(inputImage: Image.Image, factor: float) -> Image.Image:
    # Create the enhancement tool
    enhance = ImageEnhance.Contrast(inputImage)

    # Manipulate the image
    return enhance.enhance(factor)

def Brightness(inputImage: Image.Image, factor: float) -> Image.Image:
    # Create the enhancement tool
    enhance = ImageEnhance.Brightness(inputImage)

    # Manipulate the image
    return enhance.enhance(factor)

def Denoise(inputImage: Image.Image) -> Image.Image:
    # Convert the Pillow image to an OpenCV image
    opencvImage = cvtColor(np.array(inputImage), COLOR_RGB2BGR)

    # Denoise the image
    denoisedImage = fastNlMeansDenoisingColored(opencvImage, None, 3, 3, 7, 21)  # type: ignore

    # Convert the OpenCV image to a Pillow image
    return Image.fromarray(cvtColor(denoisedImage, COLOR_BGR2RGB))

def SuperResolution(inputImage: Image.Image, factor: int) -> Image.Image:
    if factor >= 2 and factor <= 4:
        # Create the super resolution object
        sr = dnn_superres.DnnSuperResImpl_create()

        # Convert the Pillow image to an OpenCV image
        opencvImage = cvtColor(np.array(inputImage), COLOR_RGB2BGR)

        # Create the model path
        modelPath = f'ImageViewer/Resources/FSRCNN_x{factor}.pb'

        # Read the model
        sr.readModel(modelPath)

        # Set the model to use
        sr.setModel('fsrcnn', factor)

        # Upscale the image
        upscaledImage = sr.upsample(opencvImage)

        # Convert the OpenCV image to a Pillow image
        return Image.fromarray(cvtColor(upscaledImage, COLOR_BGR2RGB))
    else:
        # Log the error
        logging.log(logging.ERROR, f'Invalid super resolution factor: {factor}')

        # Return the original image
        return inputImage
