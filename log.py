import time
# Add time to message
def log(string):
    return '[%s]%s' % (time.strftime('%H:%M:%S'), string)