import os, sys, time, select, tty, json, base64, zlib, subprocess, shutil

WORK    = sys.argv[1]
STATE   = f'{WORK}/state'
HOST    = f'{WORK}/mru-host'
BINARY  = f'{os.path.dirname(os.path.abspath(__file__))}/../Main/build/esp32.esp32.esp32s3/Main.ino.bin'
CHUNK   = 2048
BOOT    = 4.5    # s ATÉ O FIRMWARE RESPONDER, COM A BUSCA DO KERNEL
RESTART = 4.5    # s DEPOIS DE UM REINÍCIO
PROOF   = 11     # s PARA O FIRMWARE NOVO SAIR DA PROVA DE 10 s
results = []


def check(name, ok, detail=''):
    results.append(bool(ok))
    print('PASS' if ok else 'FAIL', name, str(detail)[:230], flush=True)


def control(name, value):
    with open(f'{STATE}/{name}', 'w') as file:
        file.write(value)


def getFlag(name):
    with open(f'{STATE}/{name}') as file:
        return file.read().strip()


def launch():
    env = {key: value for key, value in os.environ.items() if not key.endswith('_FD')}
    env['MRU_STATE'] = STATE
    subprocess.Popen([HOST], env=env, stdout=open(f'{WORK}/run.log', 'w'), stderr=subprocess.STDOUT)


# UM FIRMWARE NOVO EM FOLHA: NVS E PARTIÇÕES VAZIAS, OU COM A FALHA DO KERNEL PEDIDA DESDE O BOOT
def boot(kernel=None, wait=BOOT):
    subprocess.run(['pkill', '-x', 'mru-host'])
    time.sleep(0.2)
    shutil.rmtree(STATE, ignore_errors=True)
    os.makedirs(STATE)

    if kernel:
        control('kernel', kernel)

    launch()
    time.sleep(wait)
    return Port(getFlag('rs232'))


# A PONTA DO COMPUTADOR NO PTY: COMANDOS, RESPOSTAS E AS PERGUNTAS DE DIAGNÓSTICO
class Port:
    def __init__(self, path):
        self.fd     = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        self.buffer = b''
        tty.setraw(self.fd)

    def send(self, text):
        data  = text.encode()
        index = 0

        while index < len(data):
            try:
                index += os.write(self.fd, data[index:index + 256])
            except BlockingIOError:
                pass

            time.sleep(0.001)

    def read(self, seconds, until=None):
        end    = time.time() + seconds
        output = []

        while time.time() < end:
            if select.select([self.fd], [], [], 0.02)[0]:
                try:
                    self.buffer += os.read(self.fd, 8192)
                except OSError:
                    time.sleep(0.05)

            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                output.append(line.decode('utf8', 'replace').strip())

                if until and until in output[-1]:
                    return output

        return output

    def ask(self, command, until, seconds=3):
        self.read(0.02)
        self.send(command + '\r\n')
        return next((line for line in self.read(seconds, until) if until in line), None)

    def info(self):
        answer = self.ask('$diagnostics!', '"uptime"')
        return json.loads(answer) if answer else None

    def getLog(self):
        answer = self.ask('$log!', '"log"')
        return [entry['m'] for entry in json.loads(answer)['log']] if answer else []

    def expect(self, frame, until='$UPDATE'):
        self.send(frame)
        return (self.read(3, until) or [''])[-1]


def getFrame(index, chunk, crc=None):
    sum = zlib.crc32(chunk) if crc is None else crc
    return f'${index},{sum:08x},{base64.b64encode(chunk).decode()}!'


def getChunks(data):
    return [data[index:index + CHUNK] for index in range(0, len(data), CHUNK)]


def begin(port, data, crc=None):
    return port.ask(f'$update:{len(data)}:{zlib.crc32(data) if crc is None else crc:08x}!', '$UPDATE')


def sendAll(port, data):
    for index, chunk in enumerate(getChunks(data)):
        port.send(getFrame(index, chunk))
        port.read(5, f'OK:{index}:')


def install(port, data):
    begin(port, data)
    sendAll(port, data)
    return port.expect('$update_end!')


def testFrames(port, data):
    chunks = getChunks(data)
    answer = begin(port, data)
    check('pedido aceito', answer and 'READY:2048' in answer, answer)

    cases = [
        ('bloco com CRC errado pede de novo', getFrame(0, chunks[0], 0x1234), 'RETRY:0:crc'),
        ('bloco fora de ordem pede o certo', getFrame(5, chunks[0]), 'RETRY:0:ordem'),
        ('base64 inválido não grava', '$0,00000000,@@@@!', 'RETRY:0:crc'),
        ('quadro longo demais não estoura', '$' + 'A' * 4000 + '!', 'RETRY:0:tamanho'),
        ('outro comando no meio responde BUSY', '$status!', 'BUSY'),
        ('bloco certo grava', getFrame(0, chunks[0]), 'OK:0:2048'),
        ('repetido, com o OK perdido, confirma sem gravar de novo', getFrame(0, chunks[0]), 'OK:0:2048'),
        ('fim antes da hora recusa pelo tamanho', '$update_end!', 'ERROR:tamanho')
    ]

    for name, frame, wanted in cases:
        answer = port.expect(frame)
        check(name, wanted in answer, answer)

    info = port.info()
    check('recusa volta ao normal sem reiniciar', info and info['reset'] == 'poweron', info and info['uptime'])
    check('a partição não mudou', not os.path.exists(f'{STATE}/ota_boot'))


def testImage(port, data):
    answer = begin(port, data, 0xdeadbeef)
    check('novo pedido depois de falha', answer and 'READY' in answer, answer)
    sendAll(port, data)
    answer = port.expect('$update_end!')
    check('CRC da imagem errado recusa', 'crc da imagem' in answer, answer)
    check('a partição continua a mesma', not os.path.exists(f'{STATE}/ota_boot'))


def testRequests(port, data):
    begin(port, data)
    answer = port.expect('$update_abort!')
    check('cancelar responde ABORTED', 'ABORTED' in answer, answer)

    cases = [
        ('fim sem atualização avisa', '$update_end!', 'nenhuma atualizacao'),
        ('tamanho zero recusa', '$update:0:0!', 'pedido invalido'),
        ('imagem maior que a partição recusa', f'$update:{1 << 30}:0!', 'Not Enough Space')
    ]

    for name, command, wanted in cases:
        answer = port.ask(command, '$UPDATE')
        check(name, answer and wanted in answer, answer)


def testGone(port, data):
    begin(port, data)
    start  = time.time()
    answer = (port.read(18, '$UPDATE') or [''])[-1]
    check('o app sumiu: desiste em 15 s', 'sem dados' in answer and 14 < time.time() - start < 17, f'{time.time() - start:.1f} s {answer}')
    check('e volta a responder', port.ask('$ackoneledge!', '$MICACK!'))

    log = port.getLog()
    check('o diário conta a história', any('atualizacao falhou' in text for text in log) and any('cancelada' in text for text in log), log[-3:])


def testFlash(port, data):
    control('flash', 'fail')
    begin(port, data)
    answer = port.expect(getFrame(0, getChunks(data)[0]))
    check('erro de flash vira erro explícito', 'ERROR:Flash Write Failed' in answer, answer)
    os.unlink(f'{STATE}/flash')
    check('o firmware em uso continua depois do erro de flash', port.ask('$ackoneledge!', '$MICACK!'))


def testProof(port, data):
    answer = install(port, data)
    check('imagem certa: DONE', 'DONE' in answer, answer)
    time.sleep(RESTART)

    info = port.info()
    check('firmware novo em prova', getFlag('ota_state_app1') == 'pending' and info['partition'] == 'app1', (info['partition'], info['uptime']))
    time.sleep(max(0, PROOF - info['uptime']))
    check('10 s rodando: confirmado', getFlag('ota_state_app1') == 'valid', getFlag('ota_state_app1'))
    check('o diário registra a confirmação', any('confirmado' in text for text in port.getLog()))


def testRollback(data):
    port = boot()
    control('crash', 'boot')
    install(port, data)
    time.sleep(9)

    info = port.info()
    check('firmware novo caiu: voltou ao anterior', info and info['partition'] == 'app0' and info['rolled_back'], info and (info['partition'], info['rolled_back']))
    check('reset registrado como panic', info and info['reset'] == 'panic', info and info['reset'])

    log = port.getLog()
    check('o diário tem o boot de panic', any('reset panic' in text for text in log), log[:3])


def testCommandRestart(data):
    port = boot()
    install(port, data)
    time.sleep(4)
    check('em prova, antes do comando', getFlag('ota_state_app1') == 'pending')
    port.send('MICRS\r\n')
    time.sleep(RESTART)

    info = port.info()
    check('MICRS em prova confirma, não volta', info and info['partition'] == 'app1' and not info['rolled_back'] and getFlag('ota_state_app1') == 'valid', info and info['partition'])


def getEvents(lines):
    return [line for line in lines if line.startswith('#')]


def testKernel():
    port   = boot()
    answer = port.ask('$verbose:1!', '$VERBOSE')
    check('verbose liga', answer == '$VERBOSE ON!', answer)

    kernel = port.info()['kernel']
    check('Kernel vivo a 200 Hz', kernel['alive'] and 180 < kernel['rate'] <= 205, kernel)

    control('kernel', 'silent')
    events = getEvents(port.read(2.5))
    check('Kernel mudo: evento na porta', any(line.startswith('#E') and 'kernel mudo' in line for line in events), events)

    kernel = port.info()['kernel']
    check('Kernel mudo no diagnóstico', not kernel['alive'] and kernel['found'] and kernel['silence'] > 500, kernel)
    answer = port.ask('$check_sensor!', 'WORKING')
    check('$check_sensor! diz NOT WORKING', answer == 'NOT WORKING', answer)
    check('$status! com o sensor falso', json.loads(port.ask('$status!', '"firmware"'))['sensor'] is False)

    control('kernel', 'ok')
    events = getEvents(port.read(2.5))
    check('Kernel voltou: evento', any('voltou a transmitir' in line for line in events), events)

    control('kernel', 'bad')
    events = getEvents(port.read(2.5))
    check('checksum ruim: evento', any('checksum invalido' in line for line in events), events[:2])
    errors = port.info()['kernel']['errors']
    check('erros contados', errors > 50, errors)
    control('kernel', 'ok')
    port.read(1.2)

    control('kernel', 'frozen')
    events = getEvents(port.read(4.6))
    check('congelado: evento em 3 s', any('congelado' in line for line in events), events)
    check('congelado no diagnóstico', port.info()['kernel']['frozen'])


def testQuiet():
    port = boot()
    port.ask('$stream_start!', 'time', 1)
    check('sem verbose: nenhum evento no stream', not getEvents(port.read(1)))
    control('kernel', 'silent')
    check('sem verbose o stream continua limpo', not getEvents(port.read(2)))

    lines = [line for line in port.read(1) if line.startswith('{"time')]
    check('Kernel mudo: o stream para', len(lines) == 0, len(lines))


def testSpacing():
    port = boot()

    for gap in [0.1, 0.02, 0.0]:
        port.ask('$stream_stop!', 'nunca', 0.4)
        port.send('$stream_start!\r\n')
        time.sleep(gap)
        answer = port.ask('$ackoneledge!', '$MICACK!', 0.6)
        status = json.loads(port.ask('$status!', '"firmware"'))
        check(f'dois comandos a {int(gap * 1000)} ms: nenhum se perde', answer and status['streaming'], (answer, status['streaming']))


def testDead():
    port   = boot('dead', 6)
    answer = port.ask('$ackoneledge!', '$MICACK!')
    check('sem Kernel o MRU ainda responde', answer)

    kernel = port.info()['kernel']
    check('Kernel não achado no boot', not kernel['found'] and not kernel['alive'], kernel)

    log = port.getLog()
    check('o diário explica o boot sem Kernel', any('nao respondeu' in text for text in log), log)


with open(BINARY, 'rb') as file:
    image = file.read()

sample = image[:3 * CHUNK]
port   = boot()
testFrames(port, sample)
testImage(port, sample)
testRequests(port, sample)
testGone(port, sample)
testFlash(port, sample)
testProof(port, sample)
testRollback(sample)
testCommandRestart(sample)
testKernel()
testQuiet()
testSpacing()
testDead()
subprocess.run(['pkill', '-x', 'mru-host'])
print(f'TOTAL {len(results)} casos, {results.count(False)} FALHAS')
