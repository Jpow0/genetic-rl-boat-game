from config import *

#=---=---=---=---=---=---=---=---=---=---=---=
# RED NEURONAL 

class RedNeuronal:
    def __init__(self, pesos=None):
        if pesos:
            self.w1 = pesos[0]
            self.w2 = pesos[1]
            self.w3 = pesos[2]
            self.b1 = pesos[3]
            self.b2 = pesos[4]
            self.b3 = pesos[5]
        else:
            # caso aleatorio
            self.w1 = np.random.randn(input_size, hidden1) * 0.05
            self.w2 = np.random.randn(hidden1, hidden2) * 0.05
            self.w3 = np.random.randn(hidden2, output_size) * 0.05

            self.b1 = np.zeros(hidden1)
            self.b2 = np.zeros(hidden2)
            self.b3 = np.zeros(output_size)

# Evaluar -------------------------------------------------
    def forward(self, x):
        h1 = np.where(
            np.dot(x, self.w1) + self.b1 > 0,
            np.dot(x, self.w1) + self.b1,
            0.01 * (np.dot(x, self.w1) + self.b1)
        )

        h2 = np.where(
            np.dot(h1, self.w2) + self.b2 > 0,
            np.dot(h1, self.w2) + self.b2,
            0.01 * (np.dot(h1, self.w2) + self.b2)
        )

        o = np.tanh(0.7 * (np.dot(h2, self.w3) + self.b3))
        return o


# Mutar una red neuronal ----------------------------------
    def mutar(self, sigma=0.05):
        hijo = RedNeuronal()
        hijo.w1 = self.w1 + np.random.normal(0, sigma, self.w1.shape)
        hijo.w2 = self.w2 + np.random.normal(0, sigma, self.w2.shape)
        hijo.w3 = self.w3 + np.random.normal(0, sigma, self.w3.shape)
        hijo.b1 = self.b1 + np.random.normal(0, sigma/2, self.b1.shape)
        hijo.b2 = self.b2 + np.random.normal(0, sigma/2, self.b2.shape)
        hijo.b3 = self.b3 + np.random.normal(0, sigma/2, self.b3.shape)
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

def clip_red(red, lim=6.0):
    list(map(lambda x: np.clip(x, -lim, lim, out=x), [red.w1, red.w2, red.w3, red.b1, red.b2, red.b3]))
