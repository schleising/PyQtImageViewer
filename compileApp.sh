#! /bin/zsh

# Set the base build folder
BUILDBASE=$HOME/Downloads

# Remove any lurking build or dist folders
rm -rf $BUILDBASE/build $BUILDBASE/dist

# Create a clean environment for the build
python3 -m venv $BUILDBASE/.pqiv-build-env

# Acitivate the environment
source $BUILDBASE/.pqiv-build-env/bin/activate

# Update pip if necessary
pip3 install -U pip

# Install the requirements in the new environment
pip3 install -r requirements.txt

# Install py2app
pip3 install py2app==0.28.2

# Compile the .app
python setup.py py2app -b $BUILDBASE/build -d $BUILDBASE/dist

# Deactivate the environment
deactivate

# Remove the environment
rm -rf $BUILDBASE/.pqiv-build-env

# Let the app find the shiboken6 library
install_name_tool -add_rpath @executable_path/../Resources/lib/python3.10/shiboken6 $BUILDBASE/dist/PyQtImageViewer.app/Contents/MacOS/PyQtImageViewer

# Resign the app files
codesign --force --deep -s - $BUILDBASE/dist/PyQtImageViewer.app

# Remove the old .app from Downloads
rm -rf $BUILDBASE/PyQtImageViewer.app

# Copy the app to Downloads
mv $BUILDBASE/dist/PyQtImageViewer.app $BUILDBASE

# Create the disk image if requested
if [[ $1 == '-i' ]]; then
    # Remove the old disk image
    rm $BUILDBASE/PyQtImageViewer-Installer.dmg

    # Create the new image
    create-dmg \
    --volname "PyQtImageViewer Installer" \
    --volicon "ImageViewer/Resources/ImageViewer.icns" \
    --window-pos 200 120 \
    --window-size 600 300 \
    --icon-size 100 \
    --icon "PyQtImageViewer.app" 150 120 \
    --hide-extension "PyQtImageViewer.app" \
    --app-drop-link 450 120 \
    "$BUILDBASE/PyQtImageViewer-Installer.dmg" \
    "$BUILDBASE/PyQtImageViewer.app/"
fi

# Remove the build and dist folders
rm -rf $BUILDBASE/build $BUILDBASE/dist
