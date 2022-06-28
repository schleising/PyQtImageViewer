"""
This is a setup.py script generated by py2applet

Usage:
    python setup.py py2app
"""

from setuptools import setup

APP = ['main.py']
DATA_FILES: list[tuple[str, list[str]]] = [
    ('ImageViewer/Resources', ['ImageViewer/Resources/285658_blue_folder_icon.png', 'ImageViewer/Resources/Loading Icon.png']),
]

# A custom plist for file associations
Plist = dict(
    CFBundleDocumentTypes=[
        dict(
            CFBundleTypeExtensions=['jpeg','jpg'],
            CFBundleTypeName='JPEG image',
            CFBundleTypeRole='Viewer',
            ),
        dict(
            CFBundleTypeExtensions=['png'],
            CFBundleTypeName='PNG image',
            CFBundleTypeRole='Viewer',
            ),
        dict(
            CFBundleTypeExtensions=['gif'],
            CFBundleTypeName='GIF image',
            CFBundleTypeRole='Viewer',
            ),
        dict(
            CFBundleTypeExtensions=['webp'],
            CFBundleTypeName='WEBP image',
            CFBundleTypeRole='Viewer',
            ),
        ]
    )

OPTIONS = {
    'iconfile': 'ImageViewer/Resources/ImageViewer.icns',
    'plist': Plist,
    'packages': ['PIL'],
}

setup(
    name='PyQtImageViewer',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    version='0.0.3',
)
