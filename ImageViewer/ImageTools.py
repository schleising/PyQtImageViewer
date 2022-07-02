from typing import Callable
from PIL import Image, ImageFilter, ImageEnhance
from PIL.ImageFilter import Filter
from PIL import ImageOps

def undo(func: Callable) -> Callable:
    def wrapper(self, *args, **kwargs):
        if self._pilImage is not None:
            # Add the current image to the undo buffer
            self._undoBuffer.append(self._pilImage)

            # Call the manipulation function
            func(self, args, kwargs)

            # Update the pixmap
            self._updatePixmap()

            # Indicate that the image can be saved
            self._imageCanBeSaved = True

    return wrapper

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

def AutoContrast(inputImage: Image.Image) -> Image.Image:
    # Return the autocongtrasted image
    return ImageOps.autocontrast(inputImage)
