from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import requests
import threading
import time

app = Flask(__name__)
socketio = SocketIO(app)

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

class CurrencyObserver:
    def __init__(self):
        self.observers = {}

    def register(self, observer, currency_code):
        self.observers[observer.sid] = {'observer': observer, 'currency': currency_code}
        print(f"Клиент {observer.sid} подключился и выбрал валюту: {currency_code}")

    def unregister(self, observer):
        if observer.sid in self.observers:
            print(f"Клиент {observer.sid} отключился")
            del self.observers[observer.sid]

    def notify(self, data):
        for entry in self.observers.values():
            observer = entry['observer']
            currency_code = entry['currency']
            if currency_code in data['Valute']:
                currency_info = data['Valute'][currency_code]
                # Подготавливаем данные для отправки, включая текущий и предыдущий курс
                currency_data = {
                    'currency_code': currency_code,
                    'current_rate': currency_info['Value'],
                    'previous_rate': currency_info['Previous']
                }
                observer.update(currency_data)

class Client:
    def __init__(self, sid):
        self.sid = sid

    def update(self, data):
        socketio.emit('update', data, room=self.sid)

def get_currency_rates():
    response = requests.get('https://www.cbr-xml-daily.ru/daily_json.js')
    return response.json()

def currency_updater(observer):
    while True:
        data = get_currency_rates()
        observer.notify(data)
        time.sleep(10)

currency_observer = CurrencyObserver()

@socketio.on('connect')
def handle_connect():
    client_id = request.sid
    emit('client_id', {'id': client_id})

@socketio.on('select_currency')
def handle_select_currency(data):
    currency_code = data.get('currency_code')
    client = Client(request.sid)
    currency_observer.register(client, currency_code)
    emit('currency_selected', {'message': f'You selected {currency_code}', 'id': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    client = Client(request.sid)
    currency_observer.unregister(client)

if __name__ == "__main__":
    threading.Thread(target=currency_updater, args=(currency_observer,)).start()
    socketio.run(app, host='localhost', port=5000, allow_unsafe_werkzeug=True)