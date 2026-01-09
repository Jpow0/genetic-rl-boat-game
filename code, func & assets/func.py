#=---=---=---=---=---=---=---=---=
# LIBRERÍAS Y MÓDULOS
#=---=---=---=---=---=---=---=---=

from ursina import Entity, color
from ursina.shaders import lit_with_shadows_shader

from random import sample, shuffle, randint, choice
import numpy as np
import os

from config import *


#=---=---=---=---=---=---=---=---=
# UTILIDADES MATEMÁTICAS
#=---=---=---=---=---=---=---=---=

def normalizar(v):
    """
    Normaliza un vector.
    """
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def ruido(L):
    """
    Agrega un pequeño ruido ±0.1 a cada elemento de la lista.
    """
    return list(map(lambda x: x - choice([-0.1, 0.1]), L))


#=---=---=---=---=---=---=---=---=
# SELECCIÓN GENÉTICA
#=---=---=---=---=---=---=---=---=

def seleccion_por_torneo(poblacion, tamano_torneo=top_n):
    """
    Selección por torneo:
    - Se eligen k individuos al azar
    - Se devuelve el de mayor puntaje
    """
    participantes = sample(poblacion, tamano_torneo)
    return max(participantes, key=lambda b: b.puntaje)


#=---=---=---=---=---=---=---=---=
# GEOMETRÍA Y DISTANCIAS
#=---=---=---=---=---=---=---=---=

def dist2(a, b):
    """
    Distancia al cuadrado entre dos puntos 3D (Entity.position).
    Más rápida que usar norma.
    """
    d = a - b
    return (d.x*d.x + d.y*d.y + d.z*d.z)**(1/2)


def rocas_mas_cercanas(pos, rocas):
    """
    Devuelve las 2 rocas más cercanas a una posición.
    """
    if not rocas:
        return []
    
    rocas_ordenadas = sorted( rocas, key=lambda r: dist2(r.position, pos))

    return rocas_ordenadas[:2]


#=---=---=---=---=---=---=---=---=
# GRILLA CIRCULAR
#=---=---=---=---=---=---=---=---=

def grilla_en_radio( centro, radio, paso, y=-0.1):
    """
    Genera una grilla de puntos dentro de un radio circular sobre el plano XZ.
    """
    centro = np.array(centro)

    xs = np.arange(centro[0] - radio, centro[0] + radio + paso, paso)
    zs = np.arange(centro[2] - radio, centro[2] + radio + paso, paso)

    puntos = []
    for x in xs:
        for z in zs:
            p = np.array([x, y, z], dtype=float)

            # solo puntos dentro del radio
            if np.linalg.norm(p[[0,2]] - centro[[0,2]]) <= radio:
                puntos.append(p)

    return puntos


#=---=---=---=---=---=---=---=---=
# GENERACIÓN DE OBJETOS (PECES / DIANAS)
#=---=---=---=---=---=---=---=---=

def generar_posiciones_obj( n=3, radio_area=5.0, radio_centro_min=3.0, paso=0.5, radio_obj=3.5, c=centro ):
    """
    Genera n posiciones:
    - dentro de un radio máximo
    - lejos del centro
    - lejos entre sí
    """
    centro_np = np.array(c)

    posibles = grilla_en_radio(
        centro=centro_np,
        radio=radio_area,
        paso=paso,
        y=0
    )

    shuffle(posibles)
    obj = []

    for p in posibles:

        # -=- restricción 1: no cerca del centro
        if np.linalg.norm(p[[0,2]] - centro_np[[0,2]]) < radio_centro_min: 
            continue

        # -=- restricción 2: no cerca de otro objeto
        if any( np.linalg.norm(p[[0,2]] - q[[0,2]]) < radio_obj for q in obj):
            continue

        obj.append(p)

        if len(obj) == n:
            break

    return obj


#=---=---=---=---=---=---=---=---=
# GENERACIÓN SISTEMÁTICA DE ROCAS
#=---=---=---=---=---=---=---=---=

def rocas_prop_k_posibles( num_rocas, obj, paso=1.4,margen=0.3, c=centro, radio_area=radio_max + 0.5,  
                          radio_centro=2, radio_obj=0.4, radio_roca=0.4):
    """
    Prepara el espacio muestral de un muestreo sistematico
    de posiciones válidas para rocas.
    """
    centro_np = np.array(c)

    posibles = grilla_en_radio(
        centro=centro_np,
        radio=radio_area,
        paso=paso,
        y=-0.1
    )

    validas = []
    for p in posibles:

        # lejos del centro
        if np.linalg.norm(p[[0,2]] - centro_np[[0,2]]) < radio_centro:
            continue

        # lejos de los objetivos
        if any( np.linalg.norm(p[[0,2]] - o[[0,2]]) < (radio_obj + radio_roca + margen) for o in obj ):
            continue

        validas.append(p)

    shuffle(validas)

    prop = max(1, len(validas) // num_rocas)
    k = randint(0, prop - 1)

    return prop, k, validas


def generar_posicion_roca(i, sistematico):
    """
    Muestreamos sistematicamente según indice una posición válida
    """
    prop, k, validas = sistematico

    idx = (k + prop * i) % len(validas)
    pos = validas[idx]

    validas.pop(idx)

    return pos


#=---=---=---=---=---=---=---=---=
# VISUALES
#=---=---=---=---=---=---=---=---=

def crear_visual_obj(posiciones,scale = 1):
    """
    Crea entidades visuales a partir de posiciones.
    """
    visuales = []

    for p in posiciones:
        v = Entity(
            model='obj.bam',
            scale=scale,
            position=p,
            color=color.white66,
            shader=lit_with_shadows_shader
        )
        visuales.append(v)

    return visuales


def actualizar_visual_bote(bote, mvp, top_set):
    """
    Actualiza visualmente un bote según su estado:
    """
    if not bote.vivo:                      # muerto
        bote.color = color.red
        bote.texture = 'barco'
        bote.rotation_x -= 3
        bote.rotation_x = max(bote.rotation_x, -90)

    elif bote == mvp:                      # mejor
        bote.color = color.white
        bote.texture = 'barco'
        bote.scale = 0.275

    elif bote in top_set:                  # top
        bote.color = color.white
        bote.texture = 'barco_aux'
        bote.scale = 0.25

    else:                                 # descartable
        bote.color = color.white10
        bote.texture = 'barco_aux'
        bote.scale = 0.25

#=--=--=--=--=--=--=--=--=--=
# SERIALIZAR PESOS A TEXTO
#=--=--=--=--=--=--=--=--=--=

def red_a_texto(red):
    """
    Devuelve un string con el formato:
    pesos_iniciales = [ w1, w2, w3, b1, b2, b3 ]
    """
    def arr(a):
        return np.array2string(
            a,
            separator=', ',
            precision=8,
            suppress_small=False
        )

    texto = "pesos_iniciales = [\n\n"

    texto += "# =========================\n# w1\n# =========================\n"
    texto += f"np.array({arr(red.w1)}),\n\n"

    texto += "# =========================\n# w2\n# =========================\n"
    texto += f"np.array({arr(red.w2)}),\n\n"

    texto += "# =========================\n# w3\n# =========================\n"
    texto += f"np.array({arr(red.w3)}),\n\n"

    texto += "# =========================\n# b1\n# =========================\n"
    texto += f"np.array({arr(red.b1)}),\n\n"

    texto += "# =========================\n# b2\n# =========================\n"
    texto += f"np.array({arr(red.b2)}),\n\n"

    texto += "# =========================\n# b3\n# =========================\n"
    texto += f"np.array({arr(red.b3)})\n"

    texto += "]\n"

    return texto


#=--=--=--=--=--=--=--=--=--=
# GUARDAR MEJOR RED EN TXT
#=--=--=--=--=--=--=--=--=--=

def guardar_mejor_red_txt(mejor_bote, ciclo):
    """
    Guarda la mejor red en un .txt en la misma carpeta
    donde está este archivo .py
    """
    # carpeta del archivo actual
    carpeta_actual = os.path.dirname(os.path.abspath(__file__))

    # ruta completa del archivo
    nombre = os.path.join(carpeta_actual, "last_best_red.txt")

    with open(nombre, "w", encoding="utf-8") as f:
        f.write("# RED NEURONAL EXPORTADA AUTOMÁTICAMENTE\n")
        f.write(f"# Ciclo: {ciclo}\n")
        f.write(f"# Puntaje: {mejor_bote.puntaje:.2f}\n\n")
        f.write(red_a_texto(mejor_bote.red))

    print(f"[TXT] Mejor red guardada en:\n{nombre}")
