class NMEA:
    def __init__(self):
        self.package = [
            'roll', 'pitch', 'yaw',
            'wx', 'wy', 'wz',
            'ax', 'ay', 'az',
            'q0', 'q1', 'q2', 'q3',
            'sample_time', 'la_pos_mon_d'
        ]
        self.reset()

    def reset(self):
        self.done = False
        self.text = ''
        self.is_recording   = False
        self.asterisk_found = False
        self.checksum_chars = 0

    def update(self, newByte):
        # Detecta início de sentença
        if newByte == ord('$'):
            self.reset()
            self.is_recording = True
            self.text = '$'
            return

        if not self.is_recording:
            return

        # Converte byte → char corretamente
        self.text += chr(newByte)

        # Detecta checksum
        if self.asterisk_found:
            self.checksum_chars += 1

            # Após 2 chars do checksum, considera pacote completo
            if self.checksum_chars >= 2:
                self.done = True
                self.is_recording = False

        elif newByte == ord('*'):
            self.asterisk_found = True

    def validChecksum(self, payload, received_checksum):
        chk = 0
        for char in payload:
            chk ^= ord(char)
        calculated = f"{chk:02X}"
        return calculated.upper() == received_checksum.upper()

    def toJson(self):
        data = {}

        if not self.done or '*' not in self.text:
            return data

        try:
            content, checksum_str = self.text[1:].split('*', 1)
            checksum_str = checksum_str.strip()
        except ValueError:
            return data

        # valida checksum (usa só os 2 primeiros chars)
        if not self.validChecksum(content, checksum_str[:2]):
            return data

        fields = content.split(',')

        if len(fields) < 4 or fields[0] != 'PSXN':
            return data
        
        data_fields = fields[3:]

        if len(data_fields) < len(self.package):
            return data

        for i, var in enumerate(self.package):
            value = data_fields[i]

            if value == '':
                data[var] = None
            else:
                try:
                    data[var] = float(value)
                except ValueError:
                    data[var] = value

        return data