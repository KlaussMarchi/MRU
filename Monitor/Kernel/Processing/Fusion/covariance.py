import numpy as np

def joinData(data1, data2, w=0.5):
    (x1, p1) = data1
    (x2, p2) = data2

    p1_inv = 1.0 / p1
    p2_inv = 1.0 / p2

    pf_inv = w * p1_inv + (1.0 - w) * p2_inv
    pf = 1.0 / pf_inv
    
    xf = pf * ( w * p1_inv * x1 + (1.0 - w) * p2_inv * x2 )
    return xf, pf