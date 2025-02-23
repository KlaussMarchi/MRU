# DESKTOP
- Princípio: inicializar o sensor, (calibração), atualizar leituras e imprimir os dados como JSON.

### PASSOS PRÉVIOS

$1.$ Habilitando I2C no Raspberry Py

```
sudo raspi-config
```

- Vá em Interface Options → I2C → Enable.
- Reinicie o Raspberry se necessário.

$2.$ Instalar a biblioteca de Python para I2C (smbus)

```
sudo apt-get update
sudo apt-get install python3-smbus
```

OBS: A maioria das distribuições modernas do Raspberry Pi já vem com python3-smbus instalado, mas é bom conferir.

$3.$ Ligar o MPU6050
- Conecte SDA do MPU6050 ao pino SDA do Raspberry (normalmente GPIO2).

- Conecte SCL do MPU6050 ao pino SCL do Raspberry (normalmente GPIO3).
- Alimente o MPU6050 (3.3V ou 5V, dependendo do módulo) e GND ao terra do Raspberry.
- Se quiser conferir se o sensor está aparecendo no barramento I2C: **i2cdetect -y 1** (Deve aparecer algo em 0x68)


