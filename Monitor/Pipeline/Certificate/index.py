import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

FOLDER  = os.path.dirname(os.path.abspath(__file__))
LOGO    = f'{FOLDER}/images/measure.png'
SIGN    = f'{FOLDER}/images/signature.png'
PLOTTED = ['roll', 'pitch']    # OS DOIS ÂNGULOS QUE O PDF DESENHA

DARK   = HexColor('#3A1078')
GREEN  = HexColor('#2E7D32')
CHECK  = HexColor('#4CAF50')
TEXT   = HexColor('#333333')
GRAY   = HexColor('#E0E0E0')
HEADER = HexColor('#6A3CBC')
STRIPE = HexColor('#F3EDFA')
DEBUG  = HexColor('#C62828')

FOOTERS = {
    False: {'background': '#F0F7F0', 'color': CHECK, 'mark': '✓', 'title': 'O sistema MRU atende a todos os requisitos de calibração.', 'text': 'Recomendamos nova calibração em 12 meses.', 'tone': GREEN},
    True: {'background': '#FDECEC', 'color': DEBUG, 'mark': '!', 'title': 'Ensaio com referência em debug: a referência são os dados do próprio MRU filtrados.', 'text': 'Serve para conferir o pipeline de ponta a ponta; não atesta a calibração do MRU.', 'tone': DEBUG}
}

SECTIONS = [
    {
        'title':  'TESTES DE ACURÁCIA DE ROLL & PITCH',
        'about':  'O MRU foi submetido a movimentos dinâmicos conhecidos. Comparação entre medido e referência.',
        'axes':   PLOTTED,
        'tests':  [('RMS estático (deg)', 'rms_stat', 0.20), ('RMS dinâmico (deg)', 'rms_dyn', 0.50), ('Scale Factor', 'rms_scale_factor', 0.10)],
        'detail': True,
        'plots':  True,
        'gap':    5,
        'widths': [0.30, 0.18, 0.16, 0.16, 0.20]
    },
    {
        'title':  'TESTES DE GIROSCÓPIO',
        'about':  'Verificação através de rotações contínuas em velocidades conhecidas.',
        'axes':   ['wx', 'wy', 'wz'],
        'tests':  [('Ruído Estático STD (deg/s)', 'std_stat', 0.30)],
        'detail': False,
        'plots':  False,
        'gap':    5,
        'widths': [0.40, 0.20, 0.20, 0.20]
    },
    {
        'title':  'TESTE DE ACELERÔMETRO',
        'about':  'Verificação inclinando o MRU em degraus de 90° em um círculo completo.',
        'axes':   ['ax', 'ay', 'az'],
        'tests':  [('Ruído Estático STD (m/s²)', 'std_stat', 0.05)],
        'detail': False,
        'plots':  False,
        'gap':    15,
        'widths': [0.35, 0.22, 0.22, 0.21]
    }
]


# A FOLHA DO CERTIFICADO, DE CIMA PARA BAIXO: ESPELHO DO Calibration/Certificate
class Certificate:
    W, H   = A4
    MARGIN = 15 * mm

    def __init__(self, metrics, plots, info, output, debug=False):
        self.metrics = metrics
        self.plots   = plots
        self.info    = info
        self.output  = output
        self.debug   = debug

    def width(self):
        return self.W - 2*self.MARGIN

    def status(self, value, limit):
        return 'Aprovado' if value <= limit else 'Reprovado'

    def getHeaders(self, section):
        measured = [axis.capitalize() for axis in section['axes']] if section['detail'] else ['Medido']
        return ['Parâmetro', 'Requisito'] + measured + ['Status']

    # UMA LINHA POR REQUISITO, COM O VALOR DE CADA EIXO OU SÓ O PIOR DELES; EIXO QUE NÃO MEDIU AQUILO FICA DE FORA
    def getRows(self, section):
        rows = []

        for label, key, limit in section['tests']:
            values = [value for value in (self.metrics.get(axis, {}).get(key) for axis in section['axes']) if value is not None]

            if not values:
                continue

            cells = values if section['detail'] else [max(values)]
            rows.append([label, f'≤ {limit:.4f}'] + [f'{value:.4f}' for value in cells] + [self.status(max(values), limit)])

        return rows

    def drawHeader(self):
        c = self.canvas
        height = 55

        c.setFillColor(DARK)
        c.rect(0, self.H - height, self.W, height, fill=1, stroke=0)
        c.drawImage(LOGO, 12, self.H - height + 8, width=120, height=40, preserveAspectRatio=True, mask='auto')

        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 18); c.drawRightString(self.W - 15, self.H - 28, 'CERTIFICADO DE CALIBRAÇÃO')
        c.setFont('Helvetica', 12);      c.drawRightString(self.W - 15, self.H - 44, 'MRU')

    # OS DADOS À ESQUERDA E, À DIREITA, O TEXTO QUEBRADO NA LARGURA QUE SOBRA MAIS A ASSINATURA
    def drawInfo(self, top):
        c = self.canvas
        y = top - 10

        for label, value in self.info.items():
            c.setFillColor(TEXT)
            c.setFont('Helvetica-Bold', 7.5); c.drawString(self.MARGIN + 5, y, f'{label}:')
            c.setFont('Helvetica', 7.5);      c.drawString(self.MARGIN + 125, y, str(value))
            y -= 13

        left  = self.W/2 + 20
        limit = self.W - self.MARGIN - left - 10
        block = c.beginText(left, top - 10)
        block.setFont('Helvetica', 7)
        block.setFillColor(TEXT)
        line  = ''

        for word in 'Este certificado atesta que o sistema MRU foi calibrado conforme procedimentos internos.'.split():
            if c.stringWidth(f'{line} {word}'.strip(), 'Helvetica', 7) < limit:
                line = f'{line} {word}'.strip()
                continue

            block.textLine(line)
            line = word

        block.textLine(line)
        c.drawText(block)
        c.drawImage(SIGN, left + 60, top - 70, width=90, height=30, preserveAspectRatio=True, mask='auto')
        c.setFont('Helvetica', 6.5)
        c.drawString(left + 60, top - 78, 'Eng. de Calibração')
        return top - 100

    def drawSection(self, top, number, section):
        c = self.canvas

        c.setFont('Helvetica-Bold', 9); c.setFillColor(DARK)
        c.drawString(self.MARGIN, top, f'{number}. {section["title"]}')

        c.setFont('Helvetica', 6.5); c.setFillColor(TEXT)
        c.drawString(self.MARGIN, top - 14, section['about'])
        return top - 26

    def drawTable(self, top, headers, rows, widths):
        c      = self.canvas
        table  = self.width()
        widths = [table*fraction for fraction in widths]
        x, y   = self.MARGIN, top

        c.setFillColor(HEADER)
        c.rect(x, y - 18, table, 18, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 7)

        cx = x
        for i, header in enumerate(headers):
            c.drawCentredString(cx + widths[i]/2, y - 12, header)
            cx += widths[i]

        y -= 18

        for line, row in enumerate(rows):
            if line % 2 == 1:
                c.setFillColor(STRIPE)
                c.rect(x, y - 16, table, 16, fill=1, stroke=0)

            cx = x
            for i, cell in enumerate(row):
                approved = (str(cell) == 'Aprovado')
                c.setFillColor(GREEN if approved else TEXT)
                c.setFont('Helvetica-Bold' if approved else 'Helvetica', 6.5)
                c.drawCentredString(cx + widths[i]/2, y - 11, str(cell))
                cx += widths[i]

            y -= 16

        c.setStrokeColor(GRAY)
        c.setLineWidth(0.3)
        c.line(x, y, x + table, y)
        return y - 5

    # REFERÊNCIA x MEDIDO EM CIMA, ERRO EMBAIXO, UM ÂNGULO POR COLUNA
    def drawPlots(self, top):
        gap    = 8
        width  = (self.width() - gap) / 2
        height = width * (150/250)
        y      = top

        for name in ['ref_vs_model', 'error']:
            for column, axis in enumerate(PLOTTED):
                self.canvas.drawImage(self.plots[f'{axis}_{name}'], self.MARGIN + column*(width + gap), y - height, width=width, height=height, mask='auto')

            y -= height + 5

        return y

    # FAIXA SOB O CABEÇALHO E MARCA D'ÁGUA: A REFERÊNCIA FOI O PRÓPRIO MRU
    def drawDebug(self):
        c = self.canvas

        c.setFillColor(DEBUG)
        c.rect(0, self.H - 72, self.W, 17, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 7.5); c.drawCentredString(self.W/2, self.H - 66, 'REFERÊNCIA EM DEBUG · OS DADOS DE REFERÊNCIA SÃO OS DO PRÓPRIO MRU FILTRADOS · NÃO VALE COMO CERTIFICADO')

        c.saveState()
        c.setFillColor(DEBUG); c.setFillAlpha(0.11)
        c.translate(self.W/2, self.H/2); c.rotate(40)
        c.setFont('Helvetica-Bold', 120); c.drawCentredString(0, -40, 'DEBUG')
        c.restoreState()

    def drawFooter(self):
        c      = self.canvas
        footer = FOOTERS[self.debug]
        x, y   = self.MARGIN + 12, 17.5

        c.setFillColor(HexColor(footer['background']))
        c.rect(0, 0, self.W, 35, fill=1, stroke=0)
        c.setStrokeColor(footer['color'])
        c.setLineWidth(1)
        c.line(0, 35, self.W, 35)

        c.setFillColor(footer['color'])
        c.circle(x, y, 10, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 14); c.drawCentredString(x, y - 5, footer['mark'])

        c.setFillColor(footer['tone'])
        c.setFont('Helvetica-Bold', 6.5); c.drawString(x + 18, y + 4, footer['title'])
        c.setFillColor(TEXT)
        c.setFont('Helvetica', 5.5);      c.drawString(x + 18, y - 6, footer['text'])

        c.setFillColor(DARK)
        c.setFont('Helvetica-Bold', 7);   c.drawRightString(self.W - self.MARGIN, y + 5, 'measureoffshore.com')

    def export(self):
        missing = [axis for axis in PLOTTED if f'{axis}_error' not in self.plots]

        if missing:
            raise ValueError(f'a estratégia não estima {missing}: o certificado precisa de roll e pitch')

        self.canvas = canvas.Canvas(self.output, pagesize=A4)
        self.drawHeader()

        if self.debug:
            self.drawDebug()

        y = self.drawInfo(self.H - (82 if self.debug else 65))

        for number, section in enumerate(SECTIONS, start=1):
            y = self.drawSection(y - section['gap'], number, section)
            y = self.drawTable(y - 3, self.getHeaders(section), self.getRows(section), section['widths'])

            if section['plots']:
                y = self.drawPlots(y - 3)

        self.drawFooter()
        self.canvas.save()
        return self.output
