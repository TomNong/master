import os
from flask import Flask,redirect, request
import requests
from PIL import Image
import cv2
import time
import datetime as dt
import numpy as np
import json
from preprocess_img_test2 import *
import md5
import server_config as config



PADDING = config.PADDING
securityCode = config.securityCode
UPLOAD_FOLDER = config.UPLOAD_FOLDER
SUB_MACHINES = config.SUB_MACHINES
UPLOADPORT = config.UPLOADPORT
RESULTPORT   = config.RESULTPORT
SYMPYPORT = config.SYMPYPORT
APPDATAPATH = config.APPDATAPATH
PORT = config.PORT
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

TASK_MAP = {}
#global index
INDEX = 0
SYMPY_INDEX = 0
@app.route('/')
def hello():
  return str(time.time())

@app.route('/upload', methods=['POST'])
def upload():
    try:
      #print "upload"
      global INDEX
      global SUB_MACHINES
      global TASK_MAP
      INDEX = (INDEX + 1) % len(SUB_MACHINES)
      subIndex = INDEX
      print "index" + str(INDEX)
      print SUB_MACHINES[subIndex]
      if request.method == 'POST':
        print "got posting"
      startTime = time.time()
      file = None
      file = request.files["file"]
      filename = file.filename
      try:
        passcode = request.files["file"].filename.split(".")[0][-4:]
        print passcode
        code1 = securityCode(PADDING, int(time.time() / 60))
        code2 = securityCode(PADDING, int(time.time() / 60) - 1)
        code3 = securityCode(PADDING, int(time.time() / 60) + 1)
        print code1
        print code2
        print code3
        if code1 != passcode and code2   != passcode and code3!= passcode:
          return json.dumps({"error": "Can't access"})
      except Exception as e:
        print str(e)
        return json.dumps({"error": "Can't access"})
#      password = request.files["password"]
#      print password
      image = Image.open(file.stream)
#      image = convertToPng(image)
      print "\n got data time: " + str(time.time() - startTime)
      #logging.info("Received a file: " + filename)
      if file != None:# and allowed_file(file.filename):
        timestamp = time.time()
        #taskname = str(time.time()) + file.filename
        filename = "".join(file.filename.split(".")[:-1]) + "__" + str(dt.datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d_%H:%M:%S.%f")) + "__" + str(SUB_MACHINES[subIndex]) + ".jpg"
        #print filename
        open_cv_image = np.array(image)
        open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        open_cv_image = cv2.adaptiveThreshold(open_cv_image ,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,25,12)
        image = Image.fromarray(open_cv_image)
        image = preprocess_Img(image)
        #print SUB_MACHINES[subIndex]
        #logging.info("Store " + filename)
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename), "JPEG")
        r = requests.post("http://" + SUB_MACHINES[subIndex] + ":" + str(UPLOADPORT) + "/upload", files = {"file": open(os.path.join(app.config["UPLOAD_FOLDER"], filename),'rb')})
        print os.path.join(app.config["UPLOAD_FOLDER"], filename)
        resultJson = json.loads(r.text)
        TASK_MAP[resultJson["task_ID"]] = SUB_MACHINES[subIndex]
        print "put in TASK_MAP: " + str(TASK_MAP)
        print resultJson
        return r.text
    except Exception as e:
#      logging.error(str(e))
      print str(e)
      return json.dumps({"error" : str(e)})
#    finally:
#      try:
#        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename), "JPEG")
#      except Exception as e:
#        print str(e)

@app.route('/result', methods = ['POST', 'GET'])
def get_result():
    global TASK_MAP
    global SUB_MACHINES
    try:
      if request.headers['Content-Type'] == 'application/json':
        request_json = request.get_json()
        print request_json["task_ID"]
        print "result request" + str(request_json)
#        logging.info("Receive request for result: " + json.dumps(request_json) )
        try:
	  passcode = request_json["password"]
          print passcode
          code1 = securityCode(PADDING, int(time.time() / 60))
          code2 = securityCode(PADDING, int(time.time() / 60) - 1)
          code3 = securityCode(PADDING, int(time.time() / 60) + 1)
          print code1
          print code2
          print code3
          if code1 != passcode and code2    != passcode and code3 != passcode:
            return json.dumps({"error": "Can't access, password"})
        except Exception as e:
          print str(e)
          return json.dumps({"error": "Can't access"})
      print "TASK_MAP: " + str(TASK_MAP)
      task_ID = request_json["task_ID"]
      headers = {'Content-Type': 'application/json'}
      if task_ID in TASK_MAP:
        r = requests.get("http://" + TASK_MAP[task_ID] + ":" + str(RESULTPORT) + "/result", headers=headers, json = request_json)
        print "taskmap"
        print r.text
	del TASK_MAP[task_ID]
        return r.text
      #elif task_ID != " " or task_ID != "":
      return json.dumps({"result": "String processing...", 'isResult': 'false'})
    except Exception as e:
      #logging.error(str(e))
      return json.dumps({"error" : "result error"})


@app.route('/sympy_format', methods = ['POST', 'GET'])
def get_sympy():
    global SUB_MACHINES
    try:
      if request.headers['Content-Type'] == 'application/json':
        request_json = request.get_json()
        global SYMPY_INDEX
        SYMPY_INDEX = (SYMPY_INDEX + 1) % len(SUB_MACHINES)
        subIndex = SYMPY_INDEX
        #logging.info("Receive request for sympy_format: " + json.dumps(request_json) )
        #print request_json
        headers = {'Content-Type': 'application/json'}
        subIndex = 0
        r = requests.get("http://" + SUB_MACHINES[subIndex] + ":" + str(SYMPYPORT) + "/sympy_format", headers=headers, json = request_json)
        print r.text
        return r.text
      return json.dumps({"error" : "Format Error, Please check the request format", "isResult": "false"})
    except Exception as e:
      logging.error(str(e))
      return json.dumps({"error" : "Format Error, Please check the request format", "isResult": "false"})


@app.route('/evaluate', methods = ['POST', 'GET'])
def evaluate_res():
    try:
      if request.headers['Content-Type'] == 'application/json':
        request_json = request.get_json()
        logging.info("Receive request for evaluate_res: " + json.dumps(request_json))
        print request_json
        try:
          passcode = request_json["password"]
          print passcode
          code1 = securityCode(PADDING, int(time.time() / 60))
          code2 = securityCode(PADDING, int(time.time() / 60) - 1)
          code3 = securityCode(PADDING, int(time.time() / 60) + 1)
          print code1
          print code2
          print code3
          if code1 != passcode and code2    != passcode and code3 != passcode:
            return json.dumps({"error": "Can't access"})
        except Exception as e:
          print str(e)
          return json.dumps({"error": "Can't access"})
        field = [request_json['filename'], request_json['latex'], request_json['evaluation']]
        with open(APPDATAPATH + "evaluation.csv", "a") as f:
          f.write(field[0] + ", " + field[1] + ", " + field[2] + "\n")
        return json.dumps({"result": "saved"})
      return json.dumps({"result": "unsaved"})
    except Exception as e:
#        logging.error(str(e))
      return json.dumps({"error" : "evaluate error"})

@app.route('/feedback', methods = ['POST', 'GET'])
def feedback_res():
    try:
      if request.headers['Content-Type'] == 'application/json':
        request_json = request.get_json()
        logging.info("Receive request for evaluate_res: " + json.dumps(request_json))
        print request_json
        try:
          passcode = request_json["password"]
          print passcode
          code1 = securityCode(PADDING, int(time.time() / 60))
          code2 = securityCode(PADDING, int(time.time() / 60) - 1)
          code3 = securityCode(PADDING, int(time.time() / 60) - 1)
          print code1
          print code2
          print code3
          if code1 != passcode and code2    != passcode and code3 != passcode:
            return json.dumps({"error": "Can't access, password"})
        except Exception as e:
          print str(e)
          return json.dumps({"error": "Can't access"})
        field = [request_json['userID'], request_json['feedback'], request_json['rate']]
        with open(APPDATAPATH + "feedbacks.csv", "a") as f:
          f.write(field[0] + ", " + field[1] + ", " + field[2] + "\n")
        return json.dumps({"feedback": "saved"})
      return json.dumps({"feedback": "unsaved"})
    except Exception as e:
#        logging.error(str(e))
      return json.dumps({"error", "feedback error"})




if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', PORT))
    app.run(host='0.0.0.0', port=port, threaded=True)

