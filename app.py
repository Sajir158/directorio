from flask import Flask, jsonify, render_template, request
from collections import deque
import time
import os

app = Flask(__name__)

# =====================================================
# CONFIG
# =====================================================

MAX_SAMPLES = 500

# =====================================================
# HISTORIAL
# =====================================================

history = {

    "time": deque(maxlen=MAX_SAMPLES),

    "voltaje": deque(maxlen=MAX_SAMPLES),

    "corriente": deque(maxlen=MAX_SAMPLES),

    "potencia": deque(maxlen=MAX_SAMPLES)

}

# =====================================================
# PAGINA PRINCIPAL
# =====================================================

@app.route("/")
def index():

    return render_template("index.html")

# =====================================================
# RECIBIR DATOS ESP32
# =====================================================

@app.route("/data", methods=["POST"])
def recibir_data():

    global history

    data = request.get_json()

    if not data:

        return jsonify({

            "ok": False,

            "error": "No JSON recibido"

        }), 400

    try:

        # =================================================
        # DATOS RECIBIDOS
        # =================================================

        voltaje = float(
            data.get("voltaje", 0)
        )

        corriente1 = float(
            data.get("corriente1", 0)
        )

        corriente2 = float(
            data.get("corriente2", 0)
        )

        corriente_total = float(
            data.get("corriente_total", 0)
        )

        potencia = float(
            data.get("potencia", 0)
        )

        # =================================================
        # GUARDAR HISTORIAL
        # =================================================

        history["time"].append(
            time.strftime("%H:%M:%S")
        )

        history["voltaje"].append(
            voltaje
        )

        history["corriente"].append(
            corriente_total
        )

        history["potencia"].append(
            potencia
        )

        # =================================================
        # DEBUG SERIAL
        # =================================================

        print("--------------------------------")

        print("Voltaje:", voltaje)

        print("Corriente L1:", corriente1)

        print("Corriente L2:", corriente2)

        print("Corriente Total:", corriente_total)

        print("Potencia:", potencia)

        # =================================================
        # RESPUESTA
        # =================================================

        return jsonify({

            "ok": True,

            "samples": len(
                history["voltaje"]
            )

        })

    except Exception as e:

        return jsonify({

            "ok": False,

            "error": str(e)

        }), 400

# =====================================================
# HISTORIAL PARA GRAFICAS
# =====================================================

@app.route("/history")
def history_route():

    return jsonify({

        "time": list(history["time"]),

        "voltaje": list(history["voltaje"]),

        "corriente": list(history["corriente"]),

        "potencia": list(history["potencia"])

    })

# =====================================================
# DEBUG
# =====================================================

@app.route("/debug")
def debug():

    return jsonify({

        "samples":
        len(history["voltaje"]),

        "last_voltaje":
        history["voltaje"][-1]
        if len(history["voltaje"]) > 0
        else None,

        "last_corriente":
        history["corriente"][-1]
        if len(history["corriente"]) > 0
        else None,

        "last_potencia":
        history["potencia"][-1]
        if len(history["potencia"]) > 0
        else None,

        "history": {

            "time": list(history["time"]),

            "voltaje": list(history["voltaje"]),

            "corriente": list(history["corriente"]),

            "potencia": list(history["potencia"])

        }

    })

# =====================================================
# STATUS
# =====================================================

@app.route("/status")
def status():

    return jsonify({

        "ok": True,

        "mode": "HTTP POST",

        "samples":
        len(history["voltaje"])

    })

# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5050)
    )

    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )
