#!/bin/env python3

import sys
import mysql.connector

sys.path.append('/opt/aed/shp/lib')

import shputil

shputil.check_logged_in_user('centos')

config = shputil.get_config()

mysql_host = config['mysql_host']
mysql_user = config['mysql_user']
mysql_password = config['mysql_password']
mysql_db_name = config['mysql_db_name']

db = mysql.connector.connect(
  host=mysql_host,
  user=mysql_user,
  passwd=mysql_password,
  database=mysql_db_name
)

cursor= db.cursor()

cursor.execute("TRUNCATE TABLE dashboard_version")
cursor.execute("OPTIMIZE TABLE dashboard_version")

db.close()
