from flask import Flask, render_template, request, jsonify
import numpy as np
import math
import os


app = Flask(
    __name__,
    template_folder='vista',  # <- CAMBIO AQUÍ
    static_folder='vista'     # <- CAMBIO AQUÍ
)

# Constante de Boltzmann
k = 1.38e-23


@app.route('/')
def index():
    return render_template('index.html')

def dbm_from_watts(p_watts):
    if p_watts <= 0:
        return -9999.0
    return 10 * math.log10(p_watts / 0.001)

def watts_from_dbm(p_dbm):
    return 0.001 * (10 ** (p_dbm / 10.0))

@app.route('/api/espectro', methods=['POST'])
@app.route('/api/espectro', methods=['POST'])
def api_espectro():
    data = request.json

    T = float(data.get('temperatura', 290.0))
    ancho_banda_ruido = float(data.get('ancho_banda', 1e6))
    señales = data.get('señales', [])

    # --- Ruido térmico ---
    ruido_total_watts = k * T * ancho_banda_ruido
    ruido_total_dbm = dbm_from_watts(ruido_total_watts)

    # --- Determinar rango de frecuencias basado en todas las señales ---
    todas_frecuencias = [señal['frecuencia'] for señal in señales]
    todas_anchos = [señal['ancho_banda'] for señal in señales]
    
    f_min = min(todas_frecuencias) - max(todas_anchos) * 10
    f_max = max(todas_frecuencias) + max(todas_anchos) * 10
    freqs = np.linspace(f_min, f_max, 1000)

    # --- Ruido constante ---
    ruido_dbm = np.full_like(freqs, ruido_total_dbm)

    response = {
        "freqs": freqs.tolist(),
        "ruido_dbm": [round(x, 4) for x in ruido_dbm],
        "ruido_total_dbm": round(ruido_total_dbm, 4),
        "ruido_total_watts": round(ruido_total_watts, 20),
    }

    # --- Procesar cada señal ---
    for señal in señales:
        f_s = señal['frecuencia']
        pire_dbm = señal['pire']
        ancho_banda_senal = señal['ancho_banda']

        # Señal (parábola que cae 3 dB en ±BW/2)
        a = 3 / ((ancho_banda_senal / 2) ** 2)
        senal_dbm = pire_dbm - a * (freqs - f_s) ** 2
        senal_dbm = np.maximum(senal_dbm, ruido_total_dbm)

        f_left = f_s - (ancho_banda_senal / 2)
        f_right = f_s + (ancho_banda_senal / 2)
        nivel_3db = pire_dbm - 3

        # Añadir al response
        response[f"señal_{señal['id']}_dbm"] = [round(x, 4) for x in senal_dbm]
        response[f"señal_{señal['id']}_f_left"] = f_left
        response[f"señal_{señal['id']}_f_right"] = f_right
        response[f"señal_{señal['id']}_nivel_3db"] = nivel_3db

    return jsonify(response)


if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)
