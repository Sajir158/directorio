
from machine import Pin, ADC
import network
import time
import math
import gc
from umqtt.simple import MQTTClient

# ==========================================
# 1. CONFIGURACION WIFI
# ==========================================

WIFI_SSID = "Totalplay-129F"
WIFI_PASSWORD = "129F849B2XRF7BVM"

# ==========================================
# 2. CONFIGURACION MQTT
# ==========================================

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

MQTT_CLIENT_ID = (
    "ESP32S3_FOTOVOLTAICO_"
    + str(time.ticks_ms())
)

TOPIC_VOLTAGE = b"fotovoltaico/voltaje"
TOPIC_CURRENT = b"fotovoltaico/corriente"
TOPIC_POWER = b"fotovoltaico/potencia"

# Intervalo de publicacion: 60 segundos
INTERVALO_PUBLICACION = 60

# ==========================================
# 3. CONFIGURACION ADC
# ==========================================

ADC_MAX = 4095
VREF = 3.3

PIN_V_F1 = 4
PIN_V_F2 = 5
PIN_I_F1 = 6
PIN_I_F2 = 8

adc_v_f1 = ADC(Pin(PIN_V_F1))
adc_v_f2 = ADC(Pin(PIN_V_F2))
adc_i_f1 = ADC(Pin(PIN_I_F1))
adc_i_f2 = ADC(Pin(PIN_I_F2))

canales = [
    adc_v_f1,
    adc_v_f2,
    adc_i_f1,
    adc_i_f2
]

for adc in canales:
    adc.atten(ADC.ATTN_11DB)
    adc.width(ADC.WIDTH_12BIT)

# ==========================================
# 4. COEFICIENTES DE CALIBRACION
# ==========================================

# Voltaje fase 1
CAL_GAIN_V_F1 = 373.2719
CAL_OFFSET_V_F1 = 0.6142

# Voltaje fase 2
CAL_GAIN_V_F2 = 323.2601
CAL_OFFSET_V_F2 = 0.7617

# Corriente fase 1
CAL_GAIN_I_F1 = 0.3438
CAL_OFFSET_I_F1 = 0.0023

# Corriente fase 2
CAL_GAIN_I_F2 = 0.3473
CAL_OFFSET_I_F2 = 0.0024

# Transformadores Fronius ECS24250
# Relacion: 250 A / 333 mV

CT_FACTOR = 250.0 / 0.333

# Umbral de corriente
UMBRAL_CORRIENTE = 10.0

# ==========================================
# 5. CONFIGURACION DE MUESTREO
# ==========================================

NUM_MUESTRAS = 1000

# ==========================================
# 6. VARIABLES DE COMUNICACION
# ==========================================

wlan = network.WLAN(network.STA_IF)
mqtt_client = None

# ==========================================
# 7. FUNCION DE MEDICION RMS
# ==========================================

def medir_rms(adc):

    suma = 0.0
    suma_cuadrados = 0.0

    for i in range(NUM_MUESTRAS):

        lectura = adc.read()

        voltaje_adc = (
            lectura * VREF / ADC_MAX
        )

        suma += voltaje_adc
        suma_cuadrados += voltaje_adc ** 2

        # Aproximadamente 83 us entre muestras
        time.sleep_us(83)

    promedio = suma / NUM_MUESTRAS

    promedio_cuadrados = (
        suma_cuadrados / NUM_MUESTRAS
    )

    varianza = (
        promedio_cuadrados - promedio ** 2
    )

    if varianza < 0:
        varianza = 0

    rms = math.sqrt(varianza)

    return rms

# ==========================================
# 8. MEDICION DE VARIABLES ELECTRICAS
# ==========================================

def medir_variables():

    # Adquisicion de los cuatro canales
    rms_v_f1 = medir_rms(adc_v_f1)
    rms_v_f2 = medir_rms(adc_v_f2)

    rms_i_f1 = medir_rms(adc_i_f1)
    rms_i_f2 = medir_rms(adc_i_f2)

    # Calibracion de voltaje
    voltaje_f1 = (
        CAL_GAIN_V_F1 * rms_v_f1
        + CAL_OFFSET_V_F1
    )

    voltaje_f2 = (
        CAL_GAIN_V_F2 * rms_v_f2
        + CAL_OFFSET_V_F2
    )

    # Calibracion de corriente
    corriente_f1 = (
        CAL_GAIN_I_F1 * rms_i_f1
        + CAL_OFFSET_I_F1
    ) * CT_FACTOR

    corriente_f2 = (
        CAL_GAIN_I_F2 * rms_i_f2
        + CAL_OFFSET_I_F2
    ) * CT_FACTOR

    # Evitar valores negativos
    voltaje_f1 = max(0.0, voltaje_f1)
    voltaje_f2 = max(0.0, voltaje_f2)

    corriente_f1 = max(0.0, corriente_f1)
    corriente_f2 = max(0.0, corriente_f2)

    # Descartar corrientes menores a 10 A
    if corriente_f1 < UMBRAL_CORRIENTE:
        corriente_f1 = 0.0

    if corriente_f2 < UMBRAL_CORRIENTE:
        corriente_f2 = 0.0

    # Voltaje entre fases
    # Valido bajo el supuesto de 180 grados
    voltaje_total = voltaje_f1 + voltaje_f2

    # Corriente promedio
    corriente_promedio = (
        corriente_f1 + corriente_f2
    ) / 2.0

    # Potencia estimada
    potencia_estimada = (
        voltaje_total * corriente_promedio
    )

    return {
        "voltaje_f1": voltaje_f1,
        "voltaje_f2": voltaje_f2,
        "corriente_f1": corriente_f1,
        "corriente_f2": corriente_f2,
        "voltaje_total": voltaje_total,
        "corriente_promedio": corriente_promedio,
        "potencia_estimada": potencia_estimada
    }

# ==========================================
# 9. CONEXION WIFI
# ==========================================

def conectar_wifi():

    wlan.active(True)

    if wlan.isconnected():
        return True

    print("Conectando a Wi-Fi...")

    wlan.connect(
        WIFI_SSID,
        WIFI_PASSWORD
    )

    inicio = time.ticks_ms()

    while not wlan.isconnected():

        if time.ticks_diff(
            time.ticks_ms(), inicio
        ) > 15000:

            print("Error de conexion Wi-Fi")
            return False

        time.sleep_ms(500)

    print("Wi-Fi conectado")
    print("IP:", wlan.ifconfig()[0])

    return True

# ==========================================
# 10. CONEXION MQTT
# ==========================================

def conectar_mqtt():

    global mqtt_client

    print("Conectando al broker MQTT...")

    try:

        if mqtt_client is not None:
            try:
                mqtt_client.disconnect()
            except Exception:
                pass

        mqtt_client = MQTTClient(
            client_id=MQTT_CLIENT_ID,
            server=MQTT_BROKER,
            port=MQTT_PORT,
            keepalive=120
        )

        mqtt_client.connect()

        print("MQTT conectado correctamente")

        return True

    except Exception as error:

        print("Error MQTT:", error)

        mqtt_client = None

        return False

# ==========================================
# 11. MOSTRAR MEDICIONES
# ==========================================

def mostrar_variables(datos):

    print()
    print("========== SISTEMA INTEGRADO ==========")

    print(
        "Voltaje Fase 1: {:.2f} V".format(
            datos["voltaje_f1"]
        )
    )

    print(
        "Voltaje Fase 2: {:.2f} V".format(
            datos["voltaje_f2"]
        )
    )

    print(
        "Corriente Fase 1: {:.2f} A".format(
            datos["corriente_f1"]
        )
    )

    print(
        "Corriente Fase 2: {:.2f} A".format(
            datos["corriente_f2"]
        )
    )

    print("---------------------------------------")

    print(
        "Voltaje total: {:.2f} V".format(
            datos["voltaje_total"]
        )
    )

    print(
        "Corriente promedio: {:.2f} A".format(
            datos["corriente_promedio"]
        )
    )

    print(
        "Potencia estimada: {:.2f} W".format(
            datos["potencia_estimada"]
        )
    )

    print("=======================================")

# ==========================================
# 12. PUBLICACION MQTT
# ==========================================

def publicar_mqtt(datos):

    global mqtt_client

    if mqtt_client is None:
        return False

    try:

        voltaje = "{:.2f}".format(
            datos["voltaje_total"]
        )

        corriente = "{:.2f}".format(
            datos["corriente_promedio"]
        )

        potencia = "{:.2f}".format(
            datos["potencia_estimada"]
        )

        mqtt_client.publish(
            TOPIC_VOLTAGE,
            voltaje.encode(),
            qos=1
        )

        mqtt_client.publish(
            TOPIC_CURRENT,
            corriente.encode(),
            qos=1
        )

        mqtt_client.publish(
            TOPIC_POWER,
            potencia.encode(),
            qos=1
        )

        print()
        print("Datos publicados por MQTT")
        print("Voltaje:", voltaje, "V")
        print("Corriente:", corriente, "A")
        print("Potencia:", potencia, "W")

        return True

    except Exception as error:

        print("Error al publicar MQTT:", error)

        mqtt_client = None

        return False

# ==========================================
# 13. PROGRAMA PRINCIPAL
# ==========================================

def main():

    global mqtt_client

    print()
    print("=======================================")
    print(" MONITOREO FOTOVOLTAICO RESIDENCIAL")
    print(" ESP32-S3 - SISTEMA INTEGRADO")
    print("=======================================")

    print("Inicializando sensores...")
    time.sleep(2)

    # Intentar conexion inicial
    if conectar_wifi():
        conectar_mqtt()

    while True:

        try:

            # Medir las variables reales
            datos = medir_variables()

            # Mostrar resultados en Thonny
            mostrar_variables(datos)

            # Verificar conexion Wi-Fi
            if not wlan.isconnected():

                print("Wi-Fi desconectado")

                mqtt_client = None

                conectar_wifi()

            # Reconectar MQTT si es necesario
            if wlan.isconnected():

                if mqtt_client is None:
                    conectar_mqtt()

                if mqtt_client is not None:
                    publicar_mqtt(datos)

            gc.collect()

        except Exception as error:

            print("Error del sistema:", error)

            mqtt_client = None

        # Esperar hasta la siguiente medicion
        time.sleep(INTERVALO_PUBLICACION)


# ==========================================
# 14. EJECUCION AUTOMATICA
# ==========================================

if __name__ == "__main__":
    main()

