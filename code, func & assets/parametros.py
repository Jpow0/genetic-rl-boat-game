#=---=---=---=---=---=---=---=---=---=
# PARÁMETROS
# BOTES ------------------------------
num_botes = 25
tiempo_limite = 4
tiempo_limite_inicial = tiempo_limite
centro = [5, 0, 6]

# CONFIG RED y APRENDIZAJE -----------
input_size = 14 - 3  # entrada
hidden1 = 20     # capas ocultas
hidden2 = 10
output_size = 2 # salida izquierda/derecha y arriva/abajo

top_n = 10 # N de Ganadores

# CONIFG PECES ------------------------
peces_aleatorios = True
posiciones_peces_fijas = [[0.4, 0, 8.4 ],
                          [5.7, 0, 2.13],
                          [8.5, 0, 7   ]]

# Configuración de aprendizaje - None si se desean pesos aleatorios
pesos_iniciales = None

# Variables de control de velocidad -----
velocidad_base = 6
simulacion_rapida = False
factor_velocidad = 1

#función peces auxiliar
posiciones_peces_actuales = []

# CONFIG Rocas -----------------------
num_rocas = 20   # N rocas
umbral_choque = 0.20


# extras
frame_count = 0
top = []
mvp = None
top_set = set()

ciclo = 0
mejores_puntajes = []
promedio_puntajes = []
datos_evolucion = []

radio_max = 5

