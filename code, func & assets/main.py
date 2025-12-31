#=================================================
# LIBRERÍAS 
#=================================================

# Entorno
from math import dist
from ursina import *
from ursina.shaders import lit_with_shadows_shader
# Utilidades
from random import choice, sample
import numpy as np
import pandas as pd
# funciones y paramertros
from func import *
from red import *
from parametros import *


#=---=---=---=---=---=---=---=---=---=
# BOTE

class Bote(Entity):
    def __init__(self, red=None):
        super().__init__()

        # Config Visual --------------
        self.model = 'assets/models_compressed/barco.bam'
        self.scale = 0.25
        self.texture = 'barco'
        self.shader = lit_with_shadows_shader
        self.color = color.white

        # posición inicial ------------
        self.position = centro

        # red neuronal
        self.red = red or RedNeuronal()

        # variables de estado ----------
        self.velocidad = velocidad_base
        self.velocidad_vertical = 0
        self.vivo = True

        # entradas  ---------------------
        self.puntaje = 0
        self.descuento = 0
        self.peces_recolectados = 0
        self.roca_alcanzada = False
        self.last_x, self.last_z = self.x, self.z
        self.angulo_movimiento = 0
        self.direccion_x = 0
        self.direccion_z = 0

        # Peces ---------------------------
        self.peces_entidades = []
        self.crear_peces()

    def crear_peces(self):
        # reiniciamos peces
        for pez in self.peces_entidades:
            destroy(pez)
        self.peces_entidades.clear()

        for pos in posiciones_peces_actuales:
            p = Entity(
                model=None,
                texture=None,
                scale=0.7,
                color=color.white,
                shader=lit_with_shadows_shader,
                position=pos
            )
            self.peces_entidades.append(p)

    def reset(self):
        # posición y velocidad
        self.position = centro
        self.rotation_y = 0
        self.rotation_x = 0
        self.velocidad_vertical = 0

        # puntaje y estado
        self.puntaje = 0
        self.peces_recolectados = 0
        self.roca_alcanzada = False
        self.last_x, self.last_z = self.x, self.z
        self.angulo_movimiento = 0
        self.direccion_x = 0
        self.direccion_z = 0
        self.velocidad = velocidad_base
        self.descuento = 0

        self.vivo = True
        # recrear peces
        self.crear_peces()

    def actualizar(self): # Lógica por frame
        if not self.vivo:
            self.y -= 0.5 * time.dt
            return

        if self.peces_recolectados >= 3:
            self.y += 1 * time.dt
            return
        
        elif self.peces_recolectados < 3 and self.vivo == True:
            self.descuento -= 0.3 *time.dt*factor_velocidad / (self.peces_recolectados + 1)
 
        if np.linalg.norm([self.x-self.last_x, self.z-self.last_z]) > 0.01 and self.vivo == True:
            self.descuento -= 0.6 *time.dt*factor_velocidad

        # razonamiento para movimiento del bote
        entrada = self.obtener_entradas()
        salida = normalizar(self.red.forward(entrada))

        alpha = 0.15  # suavizado

        # Actualizar direccion según salida de la red a lo largo del tiempo
        self.direccion_x = (1-alpha)*self.direccion_x + alpha*salida[0]
        self.direccion_z = (1-alpha)*self.direccion_z + alpha*salida[1]

        self.x += self.direccion_x * time.dt * self.velocidad * factor_velocidad
        self.z += self.direccion_z * time.dt * self.velocidad * factor_velocidad

        # Actualizar rotación
        if abs(self.direccion_x) > 0.01 or abs(self.direccion_z) > 0.01:
            self.rotation_y = math.degrees(
                math.atan2(self.direccion_x, self.direccion_z)
            ) % 360

        if self.peces_entidades:
            pez = min(self.peces_entidades, key=lambda p: dist2(p.position, self.position))
            v_obj = np.array([pez.x - self.x, pez.z - self.z])
            v_obj /= np.linalg.norm(v_obj) + 1e-8

            v_mov = np.array([self.direccion_x, self.direccion_z])
            v_mov /= np.linalg.norm(v_mov) + 1e-8

            self.descuento += np.dot(v_obj, v_mov) * 0.4 * time.dt * factor_velocidad

        
        # limites del mapa
        pos = np.array([self.x, self.z])
        c = np.array(centro)[[0,2]]

        v = pos - c
        d = np.linalg.norm(v)

        if d > radio_max:
            v = v / d * radio_max
            pos = c + v
            self.x, self.z = pos


        #roca mas cercana y su distamcoa
        roca_obj = rocas_mas_cercanas(self.position,rocas)[0]
        dist_roca = dist2(self.position, roca_obj.position)
        
        # descuento por pasar cerca de una roca
        if dist_roca < umbral_choque + 0.1:
            self.descuento -= 1 *time.dt*factor_velocidad
        # animacion de choque
        
        # recolectar peces y actializar puntaje bajo distancia < 0.5
        for pez in self.peces_entidades[:]:
            if dist2(self.position, pez.position) < 0.3:
                self.peces_recolectados += 1
                destroy(pez)
                self.peces_entidades.remove(pez)
                break

        # alcanzar roca un solo fotograma
        if self.vivo and dist_roca < umbral_choque:
            self.roca_alcanzada = True
            self.vivo = False
            # castigo inmediato fuerte
            self.descuento -= 3
            animar_roca(roca_obj)

        # puntaje
        self.puntaje = (calcular_puntaje(self) * 100) / 70 + self.descuento
    
    #=---=---=---=---=---=---=---=---=
    # ENTRADAS 

    def obtener_entradas(self, radio_rocas=umbral_choque + 0.2):
        # obtenemos rocas dentro del radio
        rocas_cercanas = [d for d in rocas if dist2(self.position, d.position) <= radio_rocas]
        # ordenamos por distancia y tomamos hasta 2
        rocas_cercanas = sorted(rocas_cercanas, key=lambda d: dist2(d.position, self.position))[:2]

        # inicializamos valores por si hay menos de 2 rocas
        dir_roca_1, dist_roca_1 = 0, 0
        dir_roca_2, dist_roca_2 = 0, 0

        if len(rocas_cercanas) > 0:
            d1 = rocas_cercanas[0]
            dir_roca_1 = math.degrees(math.atan2(d1.position.x - self.position.x,
                                                d1.position.z - self.position.z))
            dist_roca_1 = dist2(self.position, d1.position)

        if len(rocas_cercanas) > 1:
            d2 = rocas_cercanas[1]
            dir_roca_2 = math.degrees(math.atan2(d2.position.x - self.position.x,
                                                d2.position.z - self.position.z))
            dist_roca_2 = dist2(self.position, d2.position)

        # dirección y distancia al pez más cercano
        if self.peces_recolectados < 3 and self.peces_entidades:
            pez_cercano = min(self.peces_entidades, key=lambda p: dist2(p.position, self.position))
            dist_pez = dist2(self.position, pez_cercano.position)
            dir_pez = math.degrees(math.atan2(pez_cercano.position.x - self.position.x,
                                            pez_cercano.position.z - self.position.z)) 
        else:
            dir_pez = 0
            dist_pez = 0

        # normalizamos entradas
        return np.array([
            self.x / 10,                    # 0-1
            self.z / 12,                    # 0-1  

            # primera roca
            math.sin(math.radians(dir_roca_1)),
            math.cos(math.radians(dir_roca_1)),
            dist_roca_1 / 12,             # 0-1

            # segunda roca
            #math.sin(math.radians(dir_roca_2)),
            #math.cos(math.radians(dir_roca_2)),
            #dist_roca_2 / 12,             # 0-1

            # pez
            math.sin(math.radians(dir_pez)),
            math.cos(math.radians(dir_pez)),
            dist_pez / 12,                 # 0-1

            self.peces_recolectados / 3,    # 0-1
            math.sin(math.radians(self.angulo_movimiento)),
            math.cos(math.radians(self.angulo_movimiento))  # -1 a 1
        ])

#=---=---=---=---=---=---=---=---=
# ANIMACIÓN de la ROCA

def animar_roca(roca):
    if getattr(roca, 'animando', False):
        return

    roca.animando = True
    pos = roca.position
    rot = roca.rotation

    dir = Vec3( uniform(-0.03, 0.03), 0.08, uniform(-0.03, 0.03))
    #rotación leve
    ang = Vec3(uniform(-8, 8), uniform(-14, 14),  uniform(-8, 8)) # X Y Z

    roca.animate_position( pos + dir, duration=0.07, curve=curve.out_quad)
    roca.animate_rotation( rot + ang, duration=0.07, curve=curve.out_quad)

    invoke(finalizar_animacion_roca, roca, pos, rot, delay=0.07)

def finalizar_animacion_roca(roca, pos, rot):
    roca.animate_position( pos, duration=0.18, curve=curve.in_out_quad )
    roca.animate_rotation( rot, duration=0.18, curve=curve.in_out_quad )

    invoke(setattr, roca, 'animando', False, delay=0.18)

#=---=---=---=---=---=---=---=---=
# CONTROL DE VELOCIDAD

def toggle_velocidad():
    global simulacion_rapida, factor_velocidad, tiempo_limite
    simulacion_rapida = not simulacion_rapida
    
    if simulacion_rapida:
        factor_velocidad = 10  # Aumenta la velocidad de la simu
        button.text = 'x10'
        button.color = color.cyan
    else:
        # Modo normal
        factor_velocidad = 1
        button.text = 'x10'
        button.color = color.white
    
    print(f"Modo {'RÁPIDO' if simulacion_rapida else 'NORMAL'} activado")

#=---=---=---=---=---=---=---=---=
# PUNTAJES

def calcular_puntaje(bote): # Función de recompenza
    
    puntaje = bote.peces_recolectados * 6

    if not bote.vivo:
        puntaje += -5   # sigue perdiendo puntos lentamente
    
    if bote.peces_recolectados >= 3 and not bote.roca_alcanzada:
        puntaje += 10  # Bonus de 10 pts por completar todos los objetivos
    return puntaje

#=---=---=---=---=---=---=---=---=
# REINICIO DE CICLO Y EVOLUCIÓN
def reiniciar_ciclo(): 
    global posiciones_peces_actuales, tiempo_restante, ciclo, mejor_bote
    
    posiciones_peces_actuales = generar_posiciones_peces()
    # actualizar peces visuales
    for v, pos in zip(visual_pez, posiciones_peces_actuales):
        v.position = pos

    peces_np = [np.array(p, dtype=float) for p in posiciones_peces_actuales]

    # rocas EVITANDO peces
    sistematico = rocas_prop_k_posibles(
        num_rocas=num_rocas,
        peces=peces_np
    )

    #  asignar posiciones
    for i, d in enumerate(rocas):
        d.position = generar_posicion_roca(i, sistematico)

    # ESTADISTICAS 
    puntajes = [b.puntaje for b in botes]

    max_puntaje, min_puntaje, avg_puntaje = max(puntajes), min(puntajes), sum(puntajes)/len(puntajes)
    # listas globales
    mejores_puntajes.append(max_puntaje)
    promedio_puntajes.append(avg_puntaje)
    
    if ciclo % 10 == 0:
        print(f'Ciclo {ciclo}: Max={max_puntaje:.1f}, min ,{min_puntaje:.1f}, Avg={avg_puntaje:.1f}')
    ciclo += 1

    # TOP 
    mejor_bote = max(botes, key=lambda b: b.puntaje)
    datos_ciclo = {
        'ciclo': ciclo,
        'puntaje': mejor_bote.puntaje,
        'peces_recolectados': mejor_bote.peces_recolectados,
        'roca_alcanzada': int(mejor_bote.roca_alcanzada),
        'w1': mejor_bote.red.w1,
        'w2': mejor_bote.red.w2,
        'w3': mejor_bote.red.w3,
        'b1': mejor_bote.red.b1,
        'b2': mejor_bote.red.b2,
        'b3': mejor_bote.red.b3
    }
    datos_evolucion.append(datos_ciclo)
    elite = sorted(botes, key=lambda b: b.puntaje, reverse=True)[:2]
    nuevas_redes = [b.red for b in elite]



# REPRODUCCIÓN Y MUTACIÓNES --------------------------------------------
    while len(nuevas_redes) < num_botes:
        padres = sorted(botes, key=lambda b: b.puntaje, reverse=True)[:top_n] # n mejores candidatos para dejar decendencia.
        tipo_descendencia = random() 

        if ciclo % 15 == 0:
            sigma = 0.15   # exploración
        else:
            sigma = 0.05   # explotación

        if tipo_descendencia < 0.30: # Decendencia 1 padre
            padre = choice( padres)
            hijo_red = padre.red  
        elif tipo_descendencia < 0.5: # Decendencia de 2 padres
            p1, p2 = sample( padres, 2 )
            hijo_red = mezclar( p1, p2 )
        elif tipo_descendencia < 0.8: # Decendencia de padre + mutación
            padre = choice( padres )
            hijo_red = padre.red.mutar(sigma=sigma)
        else: # Decendencia de 2 padres + mutación
            p1, p2 = sample( padres, 2 )
            hijo_red = mezclar( p1, p2 ).mutar(sigma=sigma)

        nuevas_redes.append(hijo_red)
    
    for bote, red in zip(botes, nuevas_redes): # aplicamos nuevas redes
        bote.red = red
        bote.reset()
    
    tiempo_restante = tiempo_limite / factor_velocidad
    
#=---=---=---=---=---=---=---=---=---=
# FUNCIÓN PARA GUARDAR DATOS 

def save_to_excel():
    df = pd.DataFrame(datos_evolucion)
    column_order = ['ciclo', 'puntaje', 'peces_recolectados', 'roca_alcanzada', 'w1', 'w2', 'w3', 'b1', 'b2', 'b3']
    df = df[column_order]
    df.to_excel('evolucion_botes.xlsx', index=False)
    print("Datos guardados en evolucion_botes.xlsx")

#=---=---=---=---=---=---=---=---=---=
# CONFIGURACIÓN URSINA

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

# DEFINIMOS ENTIDADES =---=
suelo = Entity( 
    model='plane',
    scale=(20, 1, 20),
    position=(5, 0, 5),
    texture='grass',
    texture_scale=(2, 2),
    shader=lit_with_shadows_shader
)

# =---=---=---=---=---=---=---=---=---=
# ROCA

rocas = []
posiciones_peces_actuales = generar_posiciones_peces()

for i in range(num_rocas):
    angulo = (0, randint(0, 360), 0)
    rocas_modelo = f"assets/models_compressed/roca-{choice(["1", "2","3"])}_low.bam"

    if rocas_modelo == "assets/models_compressed/roca-3_low.bam":
        aux = 4
    else:
        aux = 1
        
    size = uniform(0.35, 0.4)
    d = Entity(model=rocas_modelo, scale= size*aux, rotation=angulo, texture='rock',
        position=generar_posicion_roca(i, rocas_prop_k_posibles(num_rocas, peces=posiciones_peces_actuales)),
        shader=lit_with_shadows_shader,
        color= choice([color.white, color.dark_gray, color.light_gray,color.gray]))
    rocas.append(d)

visual_pez = []
visual_pez = crear_visual_peces(posiciones_peces_actuales)


#=---=---=---=---=---=---=---=---=---=
# PRE SIMULACIÓN

botes = [] 
for i in range(num_botes):
    if i == 0 and pesos_iniciales: # Caso con pesos y sesgos iniciales asignados
        botes.append(Bote(red=RedNeuronal(pesos=pesos_iniciales)))
    else:
        botes.append(Bote())

# casos iniciales ---------------------
tiempo_restante = tiempo_limite / factor_velocidad

texto_puntaje = Text('', position=(-0.85, 0.45), scale=1)

# Botón de control de velocidad ---------
button = Button(
    text='x10',
    color=color.white,
    position=(0.8, -0.45),
    scale=(0.1, 0.05)
)
button.on_click = toggle_velocidad

#=---=---=---=---=---=---=---=---=---=
# SIMULACIÓN

puerto = Entity(
    model='assets/models_compressed/puerto.bam',
    scale= (0.7,0.5,0.5),
    position=(-1, -0.2, 6),
    texture='rock',
    shader=lit_with_shadows_shader,
    color= color.light_gray
)

def update():
    global tiempo_restante, visual_pez,frame_count,top,mvp,top_set

# Reinicio del ciclo al terminar el tiempo 
    tiempo_restante -= time.dt
    if tiempo_restante <= 0 or all(b.peces_recolectados >= 3 for b in botes) or all(not b.vivo for b in botes):
        reiniciar_ciclo()

    for bote in botes:
        bote.actualizar()
    
    for v in visual_pez:
        v.rotation_y += 20 * time.dt

# Colores para los top n --------------
    frame_count += 1

    if frame_count % 20 == 1 or frame_count == 1:
        top = sorted(botes, key=lambda b: b.puntaje, reverse=True)[:top_n]
        mvp = top[0]
        top_set = set(top)
        
    for bote in botes:
        if not bote.vivo:
            bote.color = color.red
            bote.texture = 'barco'
            bote.rotation_x -= 3
            bote.rotation_x = max(bote.rotation_x, -90) 
            
        elif bote == mvp:
            bote.color = color.white
            bote.texture = 'barco'
            bote.scale = 0.275

        elif bote in top_set:
            bote.color = color.white
            bote.texture = 'barco_aux'
            bote.scale = 0.25
        else:
            bote.color = color.white10
            bote.texture = 'barco_aux'
            bote.scale = 0.25


    # texto
    texto_puntaje.text = f'Ciclo: {ciclo} | Tiempo: {tiempo_restante:.1f}s \n\nMejor: {int(top[0].puntaje)}'

# esc para cerrar y guardar el exel -------
def input(key):
    if key == 'escape':
        save_to_excel()
        application.quit()

app.run()