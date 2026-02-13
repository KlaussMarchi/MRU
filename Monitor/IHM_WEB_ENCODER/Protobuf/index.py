from Protobuf.telemetry_pb2 import ProtoData
import socket


UDP_IP   = "0.0.0.0"
UDP_PORT = 5005


class Protobuf:

    def setup(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((UDP_IP, UDP_PORT))
        self.data = None
        print(f"Servidor UDP aguardando em {UDP_IP}:{UDP_PORT}")


    def handle(self):
        data, addr = self.sock.recvfrom(1024)
        r = ProtoData()
    
        try:
            r.ParseFromString(data)
        except Exception as e:
            print(f"[{addr}] Erro ao decodificar Protobuf: {e}")
            return
        
        self.data = {'time': r.time, 'ax': r.ax, 'ay': r.ay, 'az': r.az, 'wx': r.wx, 'wy': r.wy, 'wz': r.wz, 'pitch': r.pitch, 'roll': r.roll, 'yaw': r.yaw}
