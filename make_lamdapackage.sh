#!/bin/bash

# Prereq for this to work:
# virtualenv virtualenv/
# source virtualenv/bin/activate
# pip install dateparser zenpy

#pip install dateparser zenpy -t virtualenv/
OLDPATH=`pwd`
TARGET_PATH=`pwd`/build/
BUILD_FILE=$OLDPATH/databotentry.zip
LAMBDA_FUNC_NAME=DataBotEntry
#echo $TARGET_PATH

## These command are for full rebuild only
##rm $BUILD_FILE
##rm -r $TARGET_PATH/*
##cp -r $OLDPATH/virtualenv/* $TARGET_PATH
##cp -r $OLDPATH/src/* $TARGET_PATH
##cd $TARGET_PATH
##zip -r $BUILD_FILE *
##cd $OLDPATH

cd $OLDPATH/src/
zip -r $BUILD_FILE *
cd $OLDPATH

aws lambda update-function-code --function-name $LAMBDA_FUNC_NAME --zip-file fileb://$BUILD_FILE


#cp -r $OLDPATH/virtualenv/lib/python2.7/site-packages/* $TARGET_PATH
#cp -r  ~/.local/lib/python2.7/site-packages/* $TARGET_PATH
