# NmapTelegramScan
# Monitoreo de Dispositivos de Red con Telegram

Este proyecto es un script en Python que utiliza `nmap` para escanear una red local y notificar sobre el estado de los dispositivos (conectados y desconectados) a través de Telegram. Ideal para administradores de redes y entusiastas que desean monitorear la presencia de dispositivos en su red de forma automatizada.

## Funcionalidades

- **Escaneo de Red**: Detecta dispositivos activos en la red usando `nmap`.
- **Monitoreo de Estado**: Realiza un seguimiento del estado de conexión y desconexión de cada dispositivo.
- **Notificaciones de Telegram**: Envía notificaciones en tiempo real a través de Telegram con el estado actual de los dispositivos documentada por dias, horas, minutos y segundos.
- **Actualización Periódica**: Actualiza el estado y las notificaciones en intervalos configurables.

## Requisitos

### Requisitos del Sistema

1. **Python**: Este script requiere Python 3.6 o superior.
2. **nmap**: Una herramienta de escaneo de redes. Debe estar instalada en tu sistema.

#### Instalación de `nmap`

- **En Windows**:
  1. Descarga el instalador desde la [página oficial de nmap](https://nmap.org/download.html).
  2. Ejecuta el instalador y sigue las instrucciones.

- **En macOS**:
  - Usa Homebrew. Si no tienes Homebrew, instálalo desde [aquí](https://brew.sh/), luego instala `nmap` con:

    ```sh
    brew install nmap
    ```

- **En Linux (Debian/Ubuntu)**:
  - Abre una terminal y ejecuta:

    ```sh
    sudo apt-get update
    sudo apt-get install nmap
    ```

- **En Linux (CentOS/RHEL)**:
  - Utiliza `yum` o `dnf`:

    ```sh
    sudo yum install nmap
    ```

    o

    ```sh
    sudo dnf install nmap
    ```

### Requisitos de Python

El script requiere la librería `requests` para interactuar con la API de Telegram. Puedes instalarla junto con otras dependencias en el archivo `requirements.txt`.

#### Instalación de Dependencias

1. Crea un archivo `requirements.txt` en el directorio del proyecto con el siguiente contenido:

    ```plaintext
    requests
    ```

2. Instala las dependencias con:

    ```sh
    pip install -r requirements.txt
    ```

## Configuración

### Archivo `config.json`

Crea un archivo llamado `config.json` en el mismo directorio que el script con el siguiente contenido:

```json
{
    "TELEGRAM_TOKEN": "TU TOKEN",
    "CHAT_ID": "TU ID",
    "NETWORK_RANGE": "192.168.1.0/24",
    "UPDATE_INTERVAL": 300
}
