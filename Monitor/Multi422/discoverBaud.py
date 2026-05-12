

from time import sleep
from Device.index import Device

def discover_baud_rate(port=None):
    # Lista dos baud rates mais comuns em equipamentos marítimos e seriais
    common_baud_rates = [4800, 9600, 19200, 38400, 57600, 115200]
    
    print("Iniciando descoberta automática de Baud Rate...")
    
    for rate in common_baud_rates:
        print(f"\n⏳ Testando baud rate: {rate} bps...")
        
        # Instancia a sua classe Device com o baud rate atual do loop
        mru = Device(port=port, rate=rate, timeout=2.0)
        mru.connect(delay=1.0)
        
        if not mru.device or not mru.device.is_open:
            print(f"⚠️ Falha ao abrir a porta. Pulando...")
            continue
            
        # Limpa o buffer para remover lixo de tentativas anteriores
        mru.clear(delay=0.5)
        
        valid_nmea_found = False
        
        # Tenta ler até 3 mensagens para confirmar
        for attempt in range(3):
            data = mru.get(timeout=2.0)
            
            if data:
                # Checa se os dados parecem ser uma sentença NMEA válida
                if '$' in data or 'PSXN' in data:
                    print(f"   Mensagem lida: {data}")
                    valid_nmea_found = True
                    break # Achou texto legível, não precisa ler mais
                else:
                    # Imprime os 20 primeiros caracteres do lixo para você ver
                    print(f"   Lixo recebido: {data[:20]}...") 
        
        # Desconecta a porta para liberar para o próximo teste
        mru.disconnect()
        sleep(0.5)
        
        if valid_nmea_found:
            print(f"\n✅ SUCESSO! O Baud rate correto em NMEA é: {rate} bps")
            return rate
            
    print("\n❌ NENHUM baud rate retornou texto legível em NMEA.")
    print("Isso confirma que o seu MRU está configurado no protocolo BINÁRIO ('MRU normal').")
    print("Você precisará do cabo de serviço e do software MRC para alterar para 'NMEA propr.'.")
    return None

# Para rodar (ele vai usar a sua função scan() se a porta for None)
if __name__ == "__main__":
    baud_correto = discover_baud_rate()