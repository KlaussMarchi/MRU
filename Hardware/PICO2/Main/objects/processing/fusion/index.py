from objects.processing.array.index import Array


def fuseCI(data1, data2, w=0.5):
    x1 = data1.get(0)
    p1 = data1.get(1)
    x2 = data2.get(0)
    p2 = data2.get(1)

    p1_inv = 1.0 / p1
    p2_inv = 1.0 / p2

    pf_inv = p1_inv * w + p2_inv * (1.0 - w)
    pf     = 1.0 / pf_inv

    xf = (x1 * (p1_inv * w) + x2 * (p2_inv * (1.0 - w))) * pf
    return xf, pf


class Fusion:
    def wx(self, w1, w2):
        data1 = Array([w1.x, w1.confidence])
        data2 = Array([w2.x, w2.confidence])
        return fuseCI(data1, data2)[0]
    
    def wy(self, w1, w2):
        data1 = Array([w1.y, w1.confidence])
        data2 = Array([w2.y, w2.confidence])
        return fuseCI(data1, data2)[0]
    
    def wz(self, w1, w2):
        data1 = Array([w1.z, w1.confidence])
        data2 = Array([w2.z, w2.confidence])
        return fuseCI(data1, data2)[0]
    
    def ax(self, a1, a2):
        data1 = Array([a1.x, a1.confidence])
        data2 = Array([a2.x, a2.confidence])
        return fuseCI(data1, data2)[0]
    
    def ay(self, a1, a2):
        data1 = Array([a1.y, a1.confidence])
        data2 = Array([a2.y, a2.confidence])
        return fuseCI(data1, data2)[0]
    
    def az(self, a1, a2):
        data1 = Array([a1.z, a1.confidence])
        data2 = Array([a2.z, a2.confidence])
        return fuseCI(data1, data2)[0]