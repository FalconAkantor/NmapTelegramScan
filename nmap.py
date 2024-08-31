import subprocess
import datetime
import json
import os
import time
import requests

# Cargar configuración desde el archivo config.json
CONFIG_FILE = 'config.json'

def load_config():
    """Carga la configuración desde un archivo JSON."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    else:
        raise FileNotFoundError(f"El archivo de configuración {CONFIG_FILE} no se encuentra.")

config = load_config()

# Configuración del bot de Telegram
TELEGRAM_TOKEN = config.get('TELEGRAM_TOKEN')
CHAT_ID = config.get('CHAT_ID')
NETWORK_RANGE = config.get('NETWORK_RANGE', '192.168.1.0/24')  # Valor por defecto
BASE_URL = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'

# Archivo donde se almacenarán las IPs y sus estados
STATE_FILE = 'ip_states.json'
UPDATE_INTERVAL = config.get('UPDATE_INTERVAL', 300)  # Valor por defecto
MESSAGE_ID_FILE = 'message_id.txt'  # Archivo para almacenar el message_id

def run_nmap_scan(network):
    """ Ejecuta nmap para escanear la red y devuelve una lista de MACs, IPs y Hostnames activas. """
    try:
        result = subprocess.run(['nmap', '-sP', network], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar nmap: {e}")
        return []

    lines = result.stdout.splitlines()

    mac_ip_pairs = []
    current_ip = None
    current_hostname = None

    for line in lines:
        if 'Nmap scan report for' in line:
            parts = line.split()
            current_hostname = parts[4] if len(parts) >= 5 else None
            current_ip = parts[-1]
        if 'MAC Address:' in line:
            mac = line.split()[2]
            if current_ip:
                mac_ip_pairs.append((mac, current_ip, current_hostname))

    return mac_ip_pairs

def load_ip_states():
    """ Carga los estados de IPs desde un archivo JSON. """
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as file:
                return json.load(file)
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}")
            return {}
    return {}

def save_ip_states(states):
    """ Guarda los estados de IPs en un archivo JSON. """
    with open(STATE_FILE, 'w') as file:
        json.dump(states, file, indent=4)

def format_duration(duration):
    """ Formatea la duración en días, horas, minutos y segundos. """
    days, seconds = divmod(duration.total_seconds(), 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

def check_ip_status(current_mac_ip_pairs):
    """ Compara las MACs e IPs actuales con los estados guardados y calcula los tiempos de conexión/desconexión. """
    now = datetime.datetime.now()
    states = load_ip_states()

    # Crear un nuevo estado para la siguiente iteración
    new_states = {}

    # Convertir la lista actual de MAC-IP a un diccionario para facilitar la búsqueda
    current_devices = {mac: (ip, hostname) for mac, ip, hostname in current_mac_ip_pairs}

    for mac, ip_hostname in current_devices.items():
        ip, hostname = ip_hostname

        if mac in states and states[mac]['status'] == 'connected':
            # Dispositivo sigue conectado
            last_seen_time = datetime.datetime.fromisoformat(states[mac]['last_seen'])
            connected_duration = datetime.timedelta(seconds=states[mac]['connected_duration'])
            connected_duration += (now - last_seen_time)

            new_states[mac] = {
                'ip': ip,
                'hostname': hostname,
                'status': 'connected',
                'first_seen': states[mac]['first_seen'],
                'last_seen': now.isoformat(),
                'connected_duration': connected_duration.total_seconds(),
                'disconnected_duration': states[mac].get('disconnected_duration', 0)
            }

        elif mac in states and states[mac]['status'] == 'disconnected':
            # Dispositivo vuelve a conectarse
            last_seen_time = datetime.datetime.fromisoformat(states[mac]['last_seen'])
            disconnected_duration = datetime.timedelta(seconds=states[mac]['disconnected_duration'])
            disconnected_duration += (now - last_seen_time)

            new_states[mac] = {
                'ip': ip,
                'hostname': hostname,
                'status': 'connected',
                'first_seen': states[mac]['first_seen'],
                'last_seen': now.isoformat(),
                'connected_duration': 0,  # Se resetea porque acaba de reconectar
                'disconnected_duration': disconnected_duration.total_seconds()  # Guardamos la duración total de la desconexión
            }

        else:
            # Dispositivo recién conectado
            new_states[mac] = {
                'ip': ip,
                'hostname': hostname,
                'status': 'connected',
                'first_seen': now.isoformat(),
                'last_seen': now.isoformat(),
                'connected_duration': 0,
                'disconnected_duration': 0
            }

    # Identificar dispositivos desconectados
    for mac, info in states.items():
        if mac not in new_states:
            if info['status'] == 'connected':
                # Dispositivo se desconectó
                last_seen_time = datetime.datetime.fromisoformat(info['last_seen'])
                connected_duration = datetime.timedelta(seconds=info['connected_duration'])
                connected_duration += (now - last_seen_time)

                new_states[mac] = {
                    'ip': info['ip'],
                    'hostname': info.get('hostname', None),
                    'status': 'disconnected',
                    'first_seen': info['first_seen'],
                    'last_seen': now.isoformat(),
                    'connected_duration': connected_duration.total_seconds(),
                    'disconnected_duration': 0  # Se resetea al desconectarse
                }

            elif info['status'] == 'disconnected':
                # Dispositivo sigue desconectado
                last_seen_time = datetime.datetime.fromisoformat(info['last_seen'])
                disconnected_duration = datetime.timedelta(seconds=info['disconnected_duration'])
                disconnected_duration += (now - last_seen_time)

                new_states[mac] = {
                    'ip': info['ip'],
                    'hostname': info.get('hostname', None),
                    'status': 'disconnected',
                    'first_seen': info['first_seen'],
                    'last_seen': now.isoformat(),
                    'connected_duration': info['connected_duration'],
                    'disconnected_duration': disconnected_duration.total_seconds()
                }

    return new_states

def format_ip_summary(states):
    """ Formatea el resumen de las MACs, IPs, Hostnames, sus estados y tiempos para enviar a Telegram. """
    connected_ips = []
    disconnected_ips = []

    for mac, info in states.items():
        status = info['status']
        ip = info['ip']
        hostname = info.get('hostname', 'N/A')

        if status == 'connected':
            connected_duration = datetime.timedelta(seconds=info['connected_duration'])
            duration_str = f"⏱️ Tiempo conectado: {format_duration(connected_duration)}"
            connected_ips.append(f"📍 MAC: {mac} | IP: {ip} | Hostname: {hostname}\n  {duration_str}\n")
        else:
            disconnected_duration = datetime.timedelta(seconds=info['disconnected_duration'])
            duration_str = f"⏱️ Tiempo desconectado: {format_duration(disconnected_duration)}"
            disconnected_ips.append(f"📍 MAC: {mac} | IP: {ip} | Hostname: {hostname}\n  {duration_str}\n")

    summary = ""

    if connected_ips:
        summary += "🟢 Dispositivos Conectados:\n" + "\n".join(connected_ips) + "\n"

    if disconnected_ips:
        summary += "🔴 Dispositivos Desconectados:\n" + "\n".join(disconnected_ips)

    return summary

def send_telegram_message(text):
    """ Envía un mensaje a Telegram y devuelve el message_id. """
    url = f"{BASE_URL}/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown'
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json().get('result', {}).get('message_id')
    except requests.exceptions.HTTPError as err:
        print(f"Error al enviar mensaje a Telegram: {err}")
        print(f"Respuesta del servidor: {err.response.content.decode('utf-8')}")
        return None

def edit_telegram_message(message_id, text):
    """ Edita un mensaje de Telegram existente. """
    url = f"{BASE_URL}/editMessageText"
    data = {
        'chat_id': CHAT_ID,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'Markdown'
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        print(f"Error al editar mensaje en Telegram: {err}")
        print(f"Respuesta del servidor: {err.response.content.decode('utf-8')}")

def main():
    """ Función principal que ejecuta el ciclo de monitoreo. """
    message_id = None

    if os.path.exists(MESSAGE_ID_FILE):
        with open(MESSAGE_ID_FILE, 'r') as file:
            message_id = int(file.read().strip())

    while True:
        print("Escaneando la red...")
        current_mac_ip_pairs = run_nmap_scan(NETWORK_RANGE)
        states = check_ip_status(current_mac_ip_pairs)
        summary = format_ip_summary(states)

        if message_id:
            edit_telegram_message(message_id, summary)
        else:
            message_id = send_telegram_message(summary)
            if message_id:
                with open(MESSAGE_ID_FILE, 'w') as file:
                    file.write(str(message_id))

        save_ip_states(states)
        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    main()

