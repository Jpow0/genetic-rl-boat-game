#=--=--=--=--=--=--=--=--=--=
# LIBRERÍAS
#=--=--=--=--=--=--=--=--=--=

# Entorno
from ursina import time,math,Vec3,invoke,curve,window,DirectionalLight,Sky,Ursina,camera,Button,Text,application
from ursina.shaders import lit_with_shadows_shader

# Utilidades
from random import choice, sample, uniform
import numpy as np

# Funciones y parámetros personalizados
from func import *
from red import *
from config import *

#=--=--=--=--=--=--=--=--=--=
# CLASE BOTE

class Bote(Entity):
    def __init__(self, red=None):
        super().__init__()

        # Configuración visual del bote
        self.model = 'assets/models_compressed/barco.bam'
        self.scale = 0.25
        self.texture = 'barco'
        self.shader = lit_with_shadows_shader
        self.color = color.white

        # Posición inicial
        self.position = centro

        # Red neuronal
        self.red = red or RedNeuronal()

        # Variables de estado
        self.velocidad = velocidad_base
        self.velocidad_vertical = 0
        self.vivo = True

        # Entradas y puntaje
        self.puntaje = 0
        self.descuento = 0
        self.obj_recolectados = 0
        self.last_x, self.last_z = 0, 0
        self.direccion_x = 0
        self.direccion_z = 0

        # Objetivos
        self.obj_entidades = []
        self.crear_obj()

    #=--=--=--=--=--=--=--=--=--=
    # Crear objivos

    def crear_obj(self):
        if not self.obj_entidades:   
            for pos in posiciones_obj_actuales:
                p = Entity(
                    model=None,
                    texture=None,
                    position=pos,
                    enabled=True)
                self.obj_entidades.append(p)

        else:
            for p, pos in zip(self.obj_entidades, posiciones_obj_actuales):
                p.position = pos
                p.enabled = True

    # =--=--=--=--=--=--=--=--=--=
    # Resetear bote

    def reset(self):
        self.position = centro
        self.rotation_y = 0
        self.rotation_x = 0
        self.velocidad_vertical = 0

        self.puntaje = 0
        self.obj_recolectados = 0
        self.last_x, self.last_z = self.x, self.z
        self.direccion_x = 0
        self.direccion_z = 0
        self.velocidad = velocidad_base
        self.descuento = 0
        self.vivo = True

        self.crear_obj()

    #=--=--=--=--=--=--=--=--=--=
    # Lógica por frame
    def actualizar(self):

        if not self.vivo:
            self.y -= 0.5 * time.dt
            return

        # Animación de ascenso al recolectar 3 objetos
        if self.obj_recolectados >= 3:
            self.y += 1 * time.dt
            return
        
        else:
            self.descuento -= (0.7 * time.dt* factor_velocidad)/ (self.obj_recolectados + 1)

        avance = abs(self.x - self.last_x) + abs(self.z - self.last_z)
        avance_esperado = self.velocidad * time.dt * factor_velocidad

        ratio = avance / (avance_esperado + 1e-8)  # evita división por 0

        if ratio < 0.2 and self.vivo:
            self.descuento -= 0.3 * time.dt * factor_velocidad
        
        # Movimiento según la red neuronal
        entrada = self.obtener_entradas()
        salida = normalizar(self.red.forward(entrada))

        alpha = 0.15 if factor_velocidad == 1 else 1
        self.direccion_x = (1 - alpha) * self.direccion_x + alpha * salida[0]
        self.direccion_z = (1 - alpha) * self.direccion_z + alpha * salida[1]

        self.last_x, self.last_z = self.x, self.z

        if factor_velocidad != 1:
            self.x += self.direccion_x * time.dt * self.velocidad * factor_velocidad/2
            self.z += self.direccion_z * time.dt * self.velocidad * factor_velocidad/2
        else:
            self.x += self.direccion_x * time.dt * self.velocidad  
            self.z += self.direccion_z * time.dt * self.velocidad 

        # Rotación según dirección
        if abs(self.direccion_x) > 0.01 or abs(self.direccion_z) > 0.01:
            self.rotation_y = math.degrees(math.atan2(self.direccion_x, self.direccion_z)) % 360

        # Interacción con el objetivo más cercano
        if self.obj_entidades:
            objetivos_activos = [o for o in self.obj_entidades if o.enabled]
            if objetivos_activos:
                objetivo = min(objetivos_activos, key=lambda p: dist2(p.position, self.position))

            v_obj = np.array([objetivo.x - self.x, objetivo.z - self.z])
            v_obj /= np.linalg.norm(v_obj) + 1e-8

            v_mov = np.array([self.direccion_x, self.direccion_z])
            v_mov /= np.linalg.norm(v_mov) + 1e-8

            self.descuento += np.dot(v_obj, v_mov) * 0.4 * time.dt 

        # Limites del mapa
        pos = np.array([self.x, self.z])
        c = np.array(centro)[[0,2]]
        v = pos - c
        d = np.linalg.norm(v)
        if d > radio_max:
            v = v / d * radio_max
            pos = c + v
            self.x, self.z = pos

        # Interacción con roca más cercana
        roca_obj = rocas_mas_cercanas(self.position, rocas)[0]
        dist_roca = dist2(self.position, roca_obj.position)

        if dist_roca < umbral_choque + 0.1:
            self.descuento -= (1/dist_roca) * time.dt 

        
        # Recolectar objetivo
        for objetivo in self.obj_entidades[:]:
            if dist2(self.position, objetivo.position) < 0.3 and objetivo.enabled:# and objetivo not in set
                self.obj_recolectados += 1
                self.descuento += 6 + self.obj_recolectados * 2
                objetivo.enabled = False
                break

        # Choque con roca
        if self.vivo and dist_roca < umbral_choque:
            self.vivo = False
            self.descuento -= 3
            if low_g == False:
                animar_roca(roca_obj)

        # Puntaje final
        self.puntaje = calcular_puntaje(self) + self.descuento

    #=--=--=--=--=--=--=--=--=--=
    # Entradas para la red neuronal
    def obtener_entradas(self, radio_rocas=umbral_choque + 0.2):
        # Rocas cercanas
        rocas_cercanas = [d for d in rocas if dist2(self.position, d.position) <= radio_rocas]
        rocas_cercanas = sorted(rocas_cercanas, key=lambda d: dist2(d.position, self.position))[:2]

        dir_roca_1, dist_roca_1 = 0, 0

        angulo_mov = math.atan2(self.direccion_x, self.direccion_z)

        if len(rocas_cercanas) > 0:
            d1 = rocas_cercanas[0]
            dir_roca_1 = math.degrees(math.atan2(d1.position.x - self.position.x, d1.position.z - self.position.z))
            dist_roca_1 = dist2(self.position, d1.position)

        # Objetivo más cercano
        # Buscar el objetivo ACTIVO más cercano
        if self.obj_recolectados < 3:

            mejor_obj = None                 # referencia al mejor objetivo encontrado
            mejor_dist2 = float('inf')       # distancia² mínima encontrada

            sx, sz = self.x, self.z          # cacheamos posición del bote (más barato)

            for o in self.obj_entidades:     # recorremos TODOS los objetivos
                if not o.enabled:            # ignorar objetivos ya recolectados
                    continue

                # Vector desde el bote al objetivo (solo XZ)
                dx = o.x - sx
                dz = o.z - sz

                # Distancia al cuadrado (evita sqrt en el loop)
                d2 = dx*dx + dz*dz

                # Si este objetivo está más cerca que el anterior
                if d2 < mejor_dist2:
                    mejor_dist2 = d2
                    mejor_obj = o

            # Si existe al menos un objetivo activo
            if mejor_obj is not None:

                # Distancia REAL (solo una raíz)
                dist_objetivo = math.sqrt(mejor_dist2)

                # Dirección hacia el objetivo (en grados, coherente con tu código)
                dir_objetivo = math.degrees(
                    math.atan2(
                        mejor_obj.x - sx,
                        mejor_obj.z - sz
                    )
                )
            else:
                # No hay objetivos activos
                dist_objetivo = 0
                dir_objetivo = 0


        return np.array([
            
            math.sin(math.radians(dir_roca_1)),
            math.cos(math.radians(dir_roca_1)),
            dist_roca_1 / radio_max,

            math.sin(math.radians(dir_objetivo)),
            math.cos(math.radians(dir_objetivo)),
            dist_objetivo / radio_max,
            
            math.sin(angulo_mov),
            math.cos(angulo_mov)
        ])

#=--=--=--=--=--=--=--=--=--=
# ANIMACIÓN DE LA ROCA
#=--=--=--=--=--=--=--=--=--=

def animar_roca(roca):
    if getattr(roca, 'animando', False):
        return

    roca.animando = True
    pos, rot = roca.position, roca.rotation
    dir = Vec3(uniform(-0.03, 0.03), 0.08, uniform(-0.03, 0.03))
    ang = Vec3(uniform(-8, 8), uniform(-14, 14), uniform(-8, 8))

    roca.animate_position(pos + dir, duration=0.07, curve=curve.out_quad)
    roca.animate_rotation(rot + ang, duration=0.07, curve=curve.out_quad)

    invoke(finalizar_animacion_roca, roca, pos, rot, delay=0.07)

def finalizar_animacion_roca(roca, pos, rot):
    roca.animate_position(pos, duration=0.18, curve=curve.in_out_quad)
    roca.animate_rotation(rot, duration=0.18, curve=curve.in_out_quad)
    invoke(setattr, roca, 'animando', False, delay=0.18)

#=--=--=--=--=--=--=--=--=--=
# BOTONES 
#=--=--=--=--=--=--=--=--=--=

def toggle_velocidad():
    global simulacion_rapida, factor_velocidad
    simulacion_rapida = not simulacion_rapida
    if simulacion_rapida:
        factor_velocidad = 10
        button.text = 'x10'
        button.color = color.azure
    else:
        factor_velocidad = 1
        button.text = 'x10'
        button.color = color.blue
    print(f"Modo {'RÁPIDO' if simulacion_rapida else 'NORMAL'} activado")


def toggle_quality():
    global fast_graphics
    fast_graphics = not fast_graphics
    if fast_graphics:
        button2.color = color.azure
        button2.text = 'LOW'
    else:
        button2.color = color.blue
        button2.text = 'LOW'
    
#=--=--=--=--=--=--=--=--=--=
# PUNTAJES
#=--=--=--=--=--=--=--=--=--=

def calcular_puntaje(bote):
    puntaje = bote.obj_recolectados * 10
    if not bote.vivo:
        puntaje += -6
    if bote.obj_recolectados >= 3:
        puntaje += 5
    return puntaje

#=--=--=--=--=--=--=--=--=--=
# REINICIO DE CICLO Y EVOLUCIÓN
#=--=--=--=--=--=--=--=--=--=

def reiniciar_ciclo():
    """
    Reinicia la simulación, genera nuevas posiciones de objetivos y rocas,
    calcula estadísticas y aplica evolución/mutaciones a las redes neuronales de los botes.
    """
    global posiciones_obj_actuales, tiempo_restante, ciclo, mejor_bote,low_g
    
    # Generar nuevas posiciones de los objetivos
    posiciones_obj_actuales = generar_posiciones_obj()
    for v, pos in zip(visual_objetivo, posiciones_obj_actuales):
        v.position = pos

    obj_np = [np.array(p, dtype=float) for p in posiciones_obj_actuales]

    # Generar posiciones de rocas evitando objetivos
    sistematico = rocas_prop_k_posibles(num_rocas=num_rocas, obj=obj_np)

    for i, d in enumerate(rocas):
        d.position = generar_posicion_roca(i, sistematico)

        low_g = fast_graphics

        if low_g == True and d.texture != None:
            d.model = "cube"
            d.texture = None
            d.color = "#AF6F43FF"
            d.scale = 0.7
            d.shader = None
            print("test")
        if low_g == False and d.texture == None:
            d.model = model_list[i]
            d.texture = 'rock'
            d.color = choice([color.white, color.dark_gray, color.light_gray, color.gray])
            aux = 4 if model_list[i].endswith('roca-3_low.bam') else 1
            size = uniform(0.3, 0.4)
            d.scale = size*aux
            d.shader = lit_with_shadows_shader
            print(d.texture)


    # Estadísticas de puntaje
    puntajes = [b.puntaje for b in botes]
    max_puntaje, min_puntaje, avg_puntaje = max(puntajes), min(puntajes), sum(puntajes)/len(puntajes)
    mejores_puntajes.append(max_puntaje)
    promedio_puntajes.append(avg_puntaje)

    if ciclo % 10 == 0:
        print(f'Ciclo {ciclo}: Max={max_puntaje:.1f}, Min={min_puntaje:.1f}, Avg={avg_puntaje:.1f}')
    ciclo += 1

    # Seleccionar mejor bote
    mejor_bote = max(botes, key=lambda b: b.puntaje)

    # Guardar mejor red cada 10 ciclos
    if ciclo % 10 == 0:
        guardar_mejor_red_txt(mejor_bote, ciclo)

    # Evolución y reproducción
    elite = sorted(botes, key=lambda b: b.puntaje, reverse=True)[:2]
    nuevas_redes = [b.red for b in elite]

    padres = sorted(botes, key=lambda b: b.puntaje, reverse=True)
    padres = padres[:top_n] + sample(padres[top_n:], k=2)

    while len(nuevas_redes) < num_botes:

        tipo_descendencia = uniform(0, 1)

        c = ciclo % 15
        sigma = (0.18 if c <= 5 or ciclo <= 30 else 0.12 if c <= 10 else 0.08 if c <= 12 else 0.05 if c <= 15 else 0.12)

        if tipo_descendencia < 0.20:  # Un padre
            padre = choice(padres)
            hijo_red = padre.red
        elif tipo_descendencia < 0.4:  # Dos padres
            p1, p2 = sample(padres, 2)
            hijo_red = mezclar(p1, p2)
        elif tipo_descendencia < 0.8:  # Padre + mutación
            padre = choice(padres)
            hijo_red = padre.red.mutar(sigma=sigma)
        else:  # Dos padres + mutación
            p1, p2 = sample(padres, 2)
            hijo_red = mezclar(p1, p2).mutar(sigma=sigma)

        #clip_red(hijo_red)
        nuevas_redes.append(hijo_red)

    # Aplicar nuevas redes a los botes
    for bote, red in zip(botes, nuevas_redes):
        bote.red = red
        if fast_graphics == True and bote.model != "cube":
            bote.model = "cube"
            bote.texture = None
            bote.color = color.gray
            bote.shader = None
        if fast_graphics == False and bote.model != "assets/models_compressed/barco.bam":
            bote.model = "assets/models_compressed/barco.bam"
            bote.shader = lit_with_shadows_shader
        bote.reset()

    tiempo_restante = tiempo_limite / factor_velocidad

#=--=--=--=--=--=--=--=--=--=
# CONFIGURACIÓN URSINA
#=--=--=--=--=--=--=--=--=--=

app = Ursina()
window.title = 'REINFORCEMENT LEARNING BOTECITO'
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = True

camera.position = (5, 10, -9.3)
camera.rotation_x = 35

DirectionalLight(y=6, z=3, rotation=(150, 35, 35), shadows=True)
Sky()

# Suelo
suelo = Entity(
    model='plane',
    scale=(20, 1, 20),
    position=(5, 0, 5),
    texture='grass',
    texture_scale=(2, 2),
    shader=lit_with_shadows_shader
)

#=--=--=--=--=--=--=--=--=--=
# ROCA Y OBJETIVOS
#=--=--=--=--=--=--=--=--=--=

rocas = []
model_list = []
posiciones_obj_actuales = generar_posiciones_obj()

for i in range(num_rocas):
    angulo = (0, randint(0, 360), 0)
    rocas_modelo = f"assets/models_compressed/roca-{choice(['1','2','3'])}_low.bam"
    model_list.append(rocas_modelo)
    aux = 4 if rocas_modelo.endswith('roca-3_low.bam') else 1
    size = uniform(0.3, 0.4)
    d = Entity(
        model=rocas_modelo,
        scale=size*aux,
        rotation=angulo,
        texture='rock',
        position=generar_posicion_roca(i, rocas_prop_k_posibles(num_rocas, obj=posiciones_obj_actuales)),
        shader=lit_with_shadows_shader,
        color=choice([color.white, color.dark_gray, color.light_gray, color.gray])
    )
    rocas.append(d)

visual_objetivo = crear_visual_obj(posiciones_obj_actuales)

#=--=--=--=--=--=--=--=--=--=
# BOTES PRE-SIMULACIÓN
#=--=--=--=--=--=--=--=--=--=

botes = []
for i in range(num_botes):
    if i == 0 and pesos_iniciales:
        botes.append(Bote(red=RedNeuronal(pesos=pesos_iniciales)))
    else:
        botes.append(Bote())

tiempo_restante = tiempo_limite / factor_velocidad
texto_puntaje = Text('', position=(-0.85, 0.45), scale=1)

# Botón de control de velocidad
button = Button(text='x10', color=color.blue, position=(0.8, -0.45), scale=(0.1, 0.05))
button.on_click = toggle_velocidad

button2 = Button(text='LOW', color=color.blue, position=(0.8, -0.35), scale=(0.1, 0.05))
button2.on_click = toggle_quality


# Puerto
puerto = Entity(
    model='assets/models_compressed/puerto.bam',
    scale=(0.7, 0.5, 0.5),
    position=(-1, -0.2, 6),
    texture='rock',
    shader=lit_with_shadows_shader,
    color=color.light_gray )

#=--=--=--=--=--=--=--=--=--=
# UPDATE (LOOP PRINCIPAL)
#=--=--=--=--=--=--=--=--=--=

def update():
    global tiempo_restante, visual_objetivo, frame_count, top, mvp, top_set, last_time

    tiempo_restante -= time.dt
    if tiempo_restante <= 0 or all(b.obj_recolectados >= 3 for b in botes) or all(not b.vivo for b in botes):
        reiniciar_ciclo()

    for bote in botes:
        bote.actualizar()
    if low_g == False:
        for v in visual_objetivo:
            v.rotation_y += 20 * time.dt

    # Actualización top N botes
    frame_count += 1
    if frame_count % 30 == 1 or frame_count == 1:
        top = sorted(botes, key=lambda b: b.puntaje, reverse=True)[:top_n]
        mvp = top[0]
        top_set = set(top)

    for bote in botes:
        if low_g == True and bote.model != "cube":
            bote.model = "cube"
            bote.texture = None
            bote.color = color.gray
            bote.scale = [0.5, 0.5, 0.65]
        if low_g == False:
            actualizar_visual_bote(bote, mvp, top_set)

    texto_puntaje.text = f'Ciclo: {ciclo} | Tiempo: {tiempo_restante:.1f}s \n\nMejor: {int(top[0].puntaje)}'

#=--=--=--=--=--=--=--=--=--=
# INPUT (ESC PARA GUARDAR Y SALIR)
#=--=--=--=--=--=--=--=--=--=

def input(key):
    if key == 'escape':
        guardar_mejor_red_txt(mejor_bote, ciclo)
        application.quit()

#=--=--=--=--=--=--=--=--=--=
# INICIO DE LA SIMULACIÓN
#=--=--=--=--=--=--=--=--=--=

app.run()
