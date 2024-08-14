from flask import Flask, Response, request, jsonify, render_template, send_from_directory
from flask_httpauth import HTTPBasicAuth

import config.app_info as appinfo
import subprocess
import sys
import os
import datetime

flaskapp = Flask(__name__)
auth = HTTPBasicAuth()


def gen_lines(query_params, anapp):
    app = appinfo.apps[anapp]
    pemfile = app["pemloc"]
    servhost = app["host"]
    servuser = app["username"]
    servlogloc = app["logloc"]
    servlogname = app["logname"]
    servnytlead = app["nytlead"]

    dt = None
    cmd = None
    tail_ln = None
    if "date" in query_params:
        dt = query_params["date"]

    if dt is None:
        if servnytlead is not None and servnytlead != "":
            dt1 = datetime.date.today() + datetime.timedelta(days=int(servnytlead))
            dt = dt1.strftime('%Y%m%d')
        else:
            dt = datetime.datetime.now().strftime('%Y%m%d')

    if "cmd" in query_params:
        cmd = query_params["cmd"]

    if cmd is None:
        cmd = "tail"

    if "tailln" in query_params:
        tail_ln = query_params["tailln"]

    if tail_ln is None:
        tail_ln = "1000"

    yyyy = dt[0:4]
    mm = dt[4:6]
    dd = dt[6:8]

    logname_fmt = servlogname.replace('YYYY', yyyy).replace('MM', mm).replace('DD', dd)
    logfile = "%s/%s" % (servlogloc, logname_fmt)

    if cmd is None or cmd == "tail":
        ssh = subprocess.Popen(["ssh", "-i", "%s" % pemfile, "%s@%s" % (servuser, servhost),
                                 "tail", "-n%s" % tail_ln, "%s" % logfile], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        ssh = subprocess.Popen(["ssh", "-i", "%s" % pemfile, "%s@%s" % (servuser, servhost),
                                 "cat", "%s" % logfile], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    results = ssh.stdout.readlines()
    if not results:
        error = ssh.stderr.readlines()
        print(sys.stderr, "ERROR: %s" % error)
        for e in error:
            yield e
    else:
        for r in results:
            yield r

@auth.verify_password
def verify_password(username, password):
    if username == appinfo.user and password == appinfo.password:
        return username


@flaskapp.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(flaskapp.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@flaskapp.route('/<string:signal>')
@auth.login_required
def getlog(signal):
    query_params = request.args.to_dict()
    return Response(gen_lines(query_params, signal), content_type='text/plain')


@flaskapp.route('/')
@auth.login_required
def home():
    return render_template('index.html')


if __name__ == '__main__':
    flaskapp.run(host='0.0.0.0', debug=True)
