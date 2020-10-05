#!/bin/sh

DIR_NAME="SpotifyPlaylistRefresher"
BIN_NAME="$DIR_NAME.py"
TARGET_DIR="/usr/local/$DIR_NAME"

curdir=`basename $PWD`
if ([ $curdir != $DIR_NAME ]) then
    echo "This script is to be run from $DIR_NAME folder"
    exit 1
fi

myEUID=`id -u`
if ([ $myEUID -ne 0 ]) then
    echo "This script must be run with root privileges"
    exit 1
fi

# In case service is running, stop it
systemctl stop $DIR_NAME.service

mkdir -p $TARGET_DIR
mkdir -p $TARGET_DIR/templates
mkdir -p $TARGET_DIR/templates/css
mkdir -p $TARGET_DIR/templates/images
mkdir -p $TARGET_DIR/system

cp $BIN_NAME $TARGET_DIR
cp README.md $TARGET_DIR

cp system/$DIR_NAME.service $TARGET_DIR/system

if ([ ! -d "$TARGET_DIR/secret" ]) then
    mkdir -p $TARGET_DIR/secret
    cp secret/certificate.crt $TARGET_DIR/secret
    cp secret/private.key $TARGET_DIR/secret
    chmod 0500 $TARGET_DIR/secret/private.key
fi

cp templates/index.html $TARGET_DIR/templates
cp templates/about.html $TARGET_DIR/templates
cp templates/contact.html $TARGET_DIR/templates
cp templates/refresher.html $TARGET_DIR/templates

cp templates/css/style.css $TARGET_DIR/templates/css

cp templates/images/Gokul.jpg $TARGET_DIR/templates/images

# Setup service
rm /etc/systemd/system/$DIR_NAME.service
ln -s $TARGET_DIR/system/$DIR_NAME.service /etc/systemd/system/$DIR_NAME.service
systemctl daemon-reload

echo "You may run "'"sudo systemctl start '$DIR_NAME.service'"'" when you are ready"

