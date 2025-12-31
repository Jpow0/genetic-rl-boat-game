import numpy as np
from parametros import *

#=---=---=---=---=---=---=---=---=---=---=---=
# RED NEURONAL 

class RedNeuronal:
    def __init__(self, pesos=None):
        if pesos:
            self.w1 = pesos['w1']
            self.w2 = pesos['w2']
            self.w3 = pesos['w3']
            self.b1 = pesos['b1']
            self.b2 = pesos['b2']
            self.b3 = pesos['b3']
        else:
            # caso aleatorio
            self.w1 = np.random.randn(input_size, hidden1) * np.sqrt(2 / input_size)
            self.w2 = np.random.randn(hidden1, hidden2) * np.sqrt(2 / hidden1)
            self.w3 = np.random.randn(hidden2, output_size) * 0.1
            self.b1 = np.zeros(hidden1)
            self.b2 = np.zeros(hidden2)
            self.b3 = np.zeros(output_size)

# Evaluar -------------------------------------------------
    def forward(self, x):
        h1 = np.maximum(0, np.dot(x, self.w1) + self.b1)
        h2 = np.maximum(0, np.dot(h1, self.w2) + self.b2)
        o = np.tanh(np.dot(h2, self.w3) + self.b3)
        return o

# Mutar una red neuronal ----------------------------------
    def mutar(self, sigma=0.2):


        hijo = RedNeuronal()
        hijo.w1 = self.w1 + np.random.normal(0, sigma, self.w1.shape) * np.abs(self.w1)
        hijo.w2 = self.w2 + np.random.normal(0, sigma, self.w2.shape) * np.abs(self.w2)
        hijo.w3 = self.w3 + np.random.normal(0, sigma, self.w3.shape) * np.abs(self.w3)

        hijo.b1 = self.b1 + np.random.normal(0, sigma * 0.5, self.b1.shape)
        hijo.b2 = self.b2 + np.random.normal(0, sigma * 0.5, self.b2.shape)
        hijo.b3 = self.b3 + np.random.normal(0, sigma * 0.5, self.b3.shape)
        return hijo

# Mezclar dos redes neuronales -----------------------------
def mezclar(p1, p2):
    hijo = RedNeuronal()

    for attr in ['w1', 'w2', 'w3', 'b1', 'b2', 'b3']:
        a = getattr(p1.red, attr)
        b = getattr(p2.red, attr)

        mask = np.random.rand(*a.shape) < 0.5
        nuevo = np.where(mask, a, b)

        setattr(hijo, attr, nuevo.copy())

    return hijo
