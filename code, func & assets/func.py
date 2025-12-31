#=---=---=---=---=---=---=---=---=
# Librerias y módulos

from ursina import Entity, color
from ursina.shaders import lit_with_shadows_shader
from random import sample, shuffle,  randint, random, choice,uniform
import numpy as np

from parametros import *

#=---=---=---=---=---=---=---=---=
# normalizar vector de movimiento

def normalizar(v):
    n = np.linalg.norm(v)
    return v / n if n > 0 else v

def ruido(L):
    return list(map(lambda x: x - choice([-0.1, 0.1]), L))
#=---=---=---=---=---=---=---=---=
# Seelcción por torneo

def seleccion_por_torneo(poblacion, tamano_torneo=top_n): # Torneo por decendencia
    participantes = sample(poblacion, tamano_torneo)
    return max(participantes, key=lambda b: b.puntaje)

#=---=---=---=---=---=---=---=---=
# Distancia al cuadrado entre dos puntos 3D

def dist2(a, b):
    d = a - b
    return d.x*d.x + d.y*d.y + d.z*d.z

def rocas_mas_cercanas(pos, rocas):
    if not rocas:
        return []
    # Ordenamos las rocas por distancia al bote
    rocas_ordenadas = sorted(rocas, key=lambda d: dist2(d.position, pos))
    # Devolvemos las 2 primeras (o menos si hay menos de 2)
    return rocas_ordenadas[:2]

def punto_en_disco(centro, radio):
    r = radio * np.sqrt(random())   # sqrt para uniformidad
    theta = uniform(0, 2*np.pi)

    x = centro[0] + r * np.cos(theta)
    z = centro[2] + r * np.sin(theta)

    return np.array([x, 0, z], dtype=float)

def generar_posiciones_peces(
    n=3,
    radio_area=5.0,
    paso=1.0,
    radio_pez=3.0,
    c=centro
):
    centro_np = np.array(c)

    posibles = grilla_en_radio(
        centro=centro_np,
        radio=radio_area,
        paso=paso,
        y=0
    )

    shuffle(posibles)
    peces = []

    for p in posibles:
        if any(
            np.linalg.norm(p[[0,2]] - q[[0,2]]) < radio_pez
            for q in peces
        ):
            continue

        peces.append(p)
        if len(peces) == n:
            break

    return peces



#=---=---=---=---=---=---=---=---=
# Generar posición roca

def grilla_en_radio(
    centro,
    radio,
    paso=1.0,
    y=-0.1
):
    centro = np.array(centro)
    xs = np.arange(centro[0] - radio, centro[0] + radio + paso, paso)
    zs = np.arange(centro[2] - radio, centro[2] + radio + paso, paso)

    puntos = []
    for x in xs:
        for z in zs:
            p = np.array([x, y, z], dtype=float)
            if np.linalg.norm(p[[0,2]] - centro[[0,2]]) <= radio:
                puntos.append(p)

    return puntos


def rocas_prop_k_posibles(
    num_rocas,
    peces,
    radio_area=radio_max,
    paso=1.0,
    radio_centro=1.0,
    radio_pez=0.4,
    radio_roca=0.4,
    margen=0.3,
    c=centro
):
    centro_np = np.array(c)

    # grilla circular
    posibles = grilla_en_radio(
        centro=centro_np,
        radio=radio_area,
        paso=paso,
        y=-0.1
    )

    validas = []
    for p in posibles:

        # cerca del centro
        if np.linalg.norm(p[[0,2]] - centro_np[[0,2]]) < radio_centro:
            continue

        # cerca de peces
        if any(
            np.linalg.norm(p[[0,2]] - pez[[0,2]])
            < (radio_pez + radio_roca + margen)
            for pez in peces
        ):
            continue

        validas.append(p)

    shuffle(validas)

    prop = max(1, len(validas) // num_rocas)
    k = randint(0, prop - 1)

    return prop, k, validas


def generar_posicion_roca(i, sistematico):
    prop, k, validas = sistematico
    idx = (k + prop*i)

    idx = idx % len(validas)  # protección
    pos = validas[idx]
    validas.pop(idx)          # 🔥 clave

    return pos


def crear_visual_peces(posiciones):
    visuales = []
    for p in posiciones:
        v = Entity(
            model='obj.bam',
            scale=1,
            position=p,
            color=color.white66,
            shader=lit_with_shadows_shader
        )
        visuales.append(v)

    return visuales