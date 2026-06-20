import sys
import os
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),"desktop"))
from app import app
print("STARTING FLASK...")
app.run(host="127.0.0.1",port=9876,debug=False)