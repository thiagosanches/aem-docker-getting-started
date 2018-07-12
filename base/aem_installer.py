import subprocess
import signal
import os
import sys
import psutil
from helpers import log, run_compaction
from optparse import OptionParser
from time import sleep

# Argument definition
usage = "usage: %prog [options] arg"
parser = OptionParser(usage)
parser.add_option("-i", "--install_file", dest="filename", help="AEM install file")
parser.add_option("-r", "--runmode", dest="runmode", help="Run mode for the installation")
parser.add_option("-p", "--port", dest="port", help="Port for instance")

options, args = parser.parse_args()
option_dic = vars(options)

# Copy out parameters
log(option_dic)
log(option_dic['filename'])
file_name = option_dic.setdefault('filename', 'cq-publish-4503.jar')
runmode = option_dic.setdefault('runmode', 'publish')
port = option_dic.setdefault('port', '4503')

# Waits for connection on LISTENER_PORT, and then checks that the returned
# success message has been recieved.
LISTENER_PORT = 50007
install_process = subprocess.Popen(['java', '-Xms8g', '-Xmx8g', '-Djava.awt.headless=true', 
  '-jar', file_name, '-listener-port', str(LISTENER_PORT), '-r', runmode, '-p', port, '-nofork'])

# Starting listener
import socket
HOST = ''
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, LISTENER_PORT))
s.listen(1)
conn, addr = s.accept()

successful_start = False
str_result = ""
while 1:
  data = conn.recv(1024)
  if not data:
    break
  else:
    str_result = str_result + str(data).strip()
    if str_result == 'started':
      successful_start = True
      break
conn.close()

# Post install hook
post_install_hook = "post_install_hook.py"
if os.path.isfile(post_install_hook):
  log("Executing post install hook")
  return_code = subprocess.call(["python", post_install_hook])
  log("Return code of process: %s" % return_code)
  log("Sleeping for 3 seconds...")
  sleep(3)
else:
  log("No install hook found")

log("Stopping instance")

# If the success message was received, attempt to close all associated processes.
if successful_start == True:
  parent_aem_process= psutil.Process(install_process.pid)
  for childProcess in parent_aem_process.get_children():
    os.kill(childProcess.pid,signal.SIGINT)

  os.kill(parent_aem_process.pid, signal.SIGINT)
  install_process.wait()

  # Run compaction
  run_compaction('/opt/aem/oak-run.jar', '/opt/aem/crx-quickstart')

  sys.exit(0)
else:
  install_process.kill()
  sys.exit(1)