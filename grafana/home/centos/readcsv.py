#import necessary modules
import csv

opt = {"csv": "/Users/regi/Library/Preferences/PyCharm2019.2/scratches/Lewisville_Transaction_Count.csv"}

with open(opt["csv"],'rt')as csvfile:
  data = csv.reader(csvfile, delimiter=';', quotechar='"')
  for row in data:
        print(row)
