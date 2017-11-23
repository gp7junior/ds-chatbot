#!/usr/bin/env python
from threading import Lock
from sklearn import datasets
from flask import Flask, Markup, render_template, session, request, send_file
from flask_socketio import SocketIO, emit, disconnect

import os.path
import sys
import json
import matplotlib.pyplot as plt, mpld3
import pandas as pd

try:
    import apiai
except ImportError:
    sys.path.append(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
    )
    import apiai

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

# Token for acces the Chatbot on DialogFlow
CLIENT_ACCESS_TOKEN = 'd0938d81c1b44088836fce3de021795b'

# dataset

labels = ["Africa", "Asia", "Europe", "Latin America", "North America"]
values = [478,5267,734,784,433]

# Dialog Flow acces functions:

def speak_json(message):
    ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN)
    request = ai.text_request()
    request.session_id = "001"
    request.query = message
    response = request.getresponse()
    parsed = json.loads(response.read())
    #print(json.dumps(parsed, indent=4, sort_keys=True))
    return(parsed)

# End of DialogFlow acces functions !

# Begining of FLask functions:
def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': count},
                      namespace='/test')
    

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)   
 
@socketio.on('send_plot', namespace='/test')
def send_plot_data():
    emit('plot_response',
        {'labels': labels, 'values': values, 'plot_option': 'bar-plot'})

def refresh_plot(labels,values):
    emit('plot_response',
        {'labels': labels, 'values': values, 'plot_option': 'bar-plot'})

# this function uses a DialogFlow call and send the response via a socket to the client
@socketio.on('say_welcome', namespace='/test')
def handle_welcome():
    ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN)
    request = ai.event_request(apiai.events.Event("welcome"))
    request.session_id = "001"

    response = request.getresponse()
    parsed = json.loads(response.read())
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('bot_response',
         {'data': parsed['result']['fulfillment']['speech'], 'count': session['receive_count'],
})
    emit('bot_request',
         {'data': 'User asked for a hifive', 'count': session['receive_count']})

def hide_column(column_name):
     
    indexToHide = [labels.index(column_name)]
 
    rangeindexToHide = range(len(values))
    newLabels = [labels[i] for i in rangeindexToHide if i not in indexToHide]
    newValues = [values[i] for i in rangeindexToHide if i not in indexToHide]

    print('I am here')
    refresh_plot(newLabels,newValues)

    
@socketio.on('send_message', namespace='/test')
def test_message(message):

    ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN)
    request = ai.text_request()
    request.session_id = "001"
    request.query = message['data']
    response = request.getresponse()
    parsed = json.loads(response.read())
    bot_speech = parsed['result']['fulfillment']['speech']
    intent = parsed['result']['metadata']['intentName']
    result = parsed['result']
    
    if (intent == 'hide_column'):
        hide_column(parsed['result']['parameters']['hidden_column'])
    elif (intent == 'show_original_plot'):
        send_plot_data();

    session['receive_count'] = session.get('receive_count', 0) + 1
    
    emit('bot_response',
         {'data': bot_speech, 
         'count': session['receive_count'], 
         'data_received': message['data'],
         'intent': intent,
         'result': result
         })
    emit('bot_request',
         {'data': message['data'], 'count': session['receive_count']})

if __name__ == '__main__':
    socketio.run(app, debug=True)
