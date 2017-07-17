#!/bin/bash

# Prereq for this to work:
# virtualenv virtualenv/
# source virtualenv/bin/activate
# pip install dateparser zenpy

#pip install dateparser zenpy -t virtualenv/
OLDPATH=`pwd`
TARGET_PATH=`pwd`/build/
BUILD_FILE=$OLDPATH/lambda_deploy_package.zip
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
zip --exclude=*viewer* -r $BUILD_FILE *
cd $OLDPATH

## aws lambda create-function --function-name session_subscribe
## aws lambda get-function --function-name session_subscribe

lambdas=( 'databot_handle_input' 'databot_session_subscribe' 'databot_session_publish' 'databot_session_get_results' )
#lambdas=( 'databot_session_publish' )
#lambdas=( 'databot_handle_input' )
for i in "${lambdas[@]}"
do
	echo "Updating " $i
  aws lambda update-function-code --function-name $i --zip-file fileb://$BUILD_FILE
done
#aws lambda update-function-code --function-name $LAMBDA_FUNC_NAME --zip-file fileb://$BUILD_FILE


#cp -r $OLDPATH/virtualenv/lib/python2.7/site-packages/* $TARGET_PATH
#cp -r  ~/.local/lib/python2.7/site-packages/* $TARGET_PATH

#aws lambda create-function \
#--region us-west-2 \
#--function-name helloworld \
#--zip-file fileb://file-path/helloworld.zip \
#--role service-role/DataBot \
#--handler helloworld.handler \
#--runtime python2.7 \
#--profile adminuser <== Whats this?
