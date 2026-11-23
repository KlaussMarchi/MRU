import os, datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FOLDER   = os.path.dirname(os.path.abspath(__file__))
LOGO     = f'{FOLDER}/images/logo.png'
SIGN     = f'{FOLDER}/images/signature.png'
PLOTTED  = ['roll', 'pitch']    # OS DOIS ÂNGULOS QUE O PDF DESENHA
PANEL    = 1.62/3.42            # ALTURA SOBRE LARGURA DOS GRÁFICOS: O figsize DO Analysis
REGULAR  = 'SourceSans3'
SEMIBOLD = 'SourceSans3-Semibold'
BOLD     = 'SourceSans3-Bold'

for name, file in [(REGULAR, 'Regular'), (SEMIBOLD, 'Semibold'), (BOLD, 'Bold')]:
    pdfmetrics.registerFont(TTFont(name, f'{FOLDER}/fonts/SourceSans3-{file}.ttf'))

DEEP   = HexColor('#3c0f78')    # A PALETA DO Documents/Datasheet: OS DOCUMENTOS DA MEASURE COM A MESMA CARA
PURPLE = HexColor('#6b39bd')
INK    = HexColor('#1f1a2e')
MUTED  = HexColor('#615b70')
LINE   = HexColor('#ddd6ea')
ZEBRA  = HexColor('#f6f4f9')
TEAL   = HexColor('#2a9d8f')
RED    = HexColor('#b42318')
AMBER  = HexColor('#b7791f')

VERDICTS = {
    'approved': {'title': 'APROVADO', 'mark': 'check', 'label': 'Aprovado', 'color': TEAL, 'ink': HexColor('#1d7468'), 'background': HexColor('#e8f5f2'), 'text': 'O MRU atende a todos os requisitos de calibração deste certificado.'},
    'failed':   {'title': 'REPROVADO', 'mark': 'cross', 'label': 'Reprovado', 'color': RED, 'ink': RED, 'background': HexColor('#fdecea'), 'text': 'O MRU não atende a todos os requisitos: os itens reprovados estão marcados nas tabelas.'},
    'debug':    {'title': 'SEM VALIDADE', 'mark': 'alert', 'color': AMBER, 'ink': HexColor('#7f5310'), 'background': HexColor('#fbf3e4'), 'text': 'Referência em debug: os dados de referência são os do próprio MRU filtrados. Confere o pipeline de ponta a ponta, não a calibração.'}
}

MARKS = {    # AS MARCAS EM TRAÇOS, NA FRAÇÃO DO TAMANHO: O ✓ DA FONTE PARECE UM √
    'check': [[(-0.45, 0.0), (-0.12, -0.34), (0.45, 0.36)]],
    'cross': [[(-0.36, -0.36), (0.36, 0.36)], [(-0.36, 0.36), (0.36, -0.36)]],
    'alert': [[(0, 0.42), (0, -0.08)], [(0, -0.38), (0, -0.39)]]
}

NOTES = ('Atesta que o MRU foi calibrado conforme os procedimentos internos da Measure Offshore; os resultados valem para o equipamento '
         'identificado, nas condições do ensaio. Erro é o ângulo medido pelo MRU menos o da plataforma de referência, nos trechos em que ela '
         'está parada (repouso) e em balanço (movimento). Recomenda-se nova calibração em 12 meses.')

SECTIONS = [
    {
        'title':   'Atitude: roll e pitch',
        'about':   'A plataforma de referência balança o MRU em pitch e em roll, e o ângulo medido é comparado ao dela em repouso e em movimento.',
        'columns': ['Roll', 'Pitch'],
        'tests':   [('Erro RMS em repouso (°)', 'rms_stat', 0.20, PLOTTED), ('Erro RMS em movimento (°)', 'rms_dyn', 0.50, PLOTTED), ('Fator de escala', 'rms_scale_factor', 0.10, PLOTTED)],
        'plots':   True
    },
    {
        'title':   'Sensores inerciais: ruído em repouso',
        'about':   'Desvio padrão de cada eixo com o MRU parado sobre a plataforma, nos trechos de repouso do ensaio.',
        'columns': ['Eixo X', 'Eixo Y', 'Eixo Z'],
        'tests':   [('Giroscópio (°/s)', 'std_stat', 0.30, ['wx', 'wy', 'wz']), ('Acelerômetro (m/s²)', 'std_stat', 0.05, ['ax', 'ay', 'az'])],
        'plots':   False
    }
]


# NÚMERO COMO SE ESCREVE NO BRASIL
def formatValue(value, digits):
    return f'{value:.{digits}f}'.replace('.', ',')


# A FOLHA DO CERTIFICADO, DE CIMA PARA BAIXO; TODO draw RECEBE O y ONDE COMEÇA E DEVOLVE O y ONDE PAROU: ESPELHO DO Calibration/Certificate
class Certificate:
    W, H   = A4
    MARGIN = 16 * mm
    ROW    = 16
    GAP    = 12

    def __init__(self, metrics, plots, number, info, output, debug=False):
        self.metrics = metrics
        self.plots   = plots
        self.number  = number
        self.info    = info
        self.output  = output
        self.debug   = debug

    def width(self):
        return self.W - 2*self.MARGIN

    # UMA LINHA POR REQUISITO COM O VALOR DE CADA EIXO; O PIOR EIXO DECIDE; REQUISITO QUE NENHUM EIXO MEDIU FICA DE FORA
    def getRows(self, section):
        rows = []

        for label, key, limit, axes in section['tests']:
            values = [self.metrics.get(axis, {}).get(key) for axis in axes]
            known  = [value for value in values if value is not None]

            if not known:
                continue

            rows.append({'label': label, 'limit': f'≤ {formatValue(limit, 2)}', 'values': ['—' if value is None else formatValue(value, 4) for value in values], 'passed': max(known) <= limit})

        return rows

    def getVerdict(self):
        rows = [row for section in SECTIONS for row in self.getRows(section)]
        return {'key': 'debug' if self.debug else 'approved' if all(row['passed'] for row in rows) else 'failed', 'passed': sum(row['passed'] for row in rows), 'total': len(rows)}

    def drawText(self, x, y, text, font, size, color, align='left', space=0):
        c = self.canvas
        c.setFont(font, size); c.setFillColor(color)
        {'left': c.drawString, 'right': c.drawRightString, 'center': c.drawCentredString}[align](x, y, text, charSpace=space)

    def drawMark(self, x, y, mark, size, color, width):
        c = self.canvas
        c.saveState()
        c.setStrokeColor(color); c.setLineWidth(width); c.setLineCap(1); c.setLineJoin(1)

        for stroke in MARKS[mark]:
            path = c.beginPath()
            path.moveTo(x + stroke[0][0]*size, y + stroke[0][1]*size)

            for dx, dy in stroke[1:]:
                path.lineTo(x + dx*size, y + dy*size)

            c.drawPath(path, stroke=1, fill=0)

        c.restoreState()

    def drawLines(self, x, y, text, font, size, color, width, leading):
        for line in simpleSplit(text, font, size, width):
            self.drawText(x, y, line, font, size, color)
            y -= leading

        return y

    # O CABEÇALHO DO DATASHEET: LOGO À ESQUERDA, O DOCUMENTO À DIREITA E O FIO ROXO EMBAIXO
    def drawHeader(self):
        c, top = self.canvas, self.H - 13*mm

        c.drawImage(LOGO, self.MARGIN, top - 36, height=42, width=42*262/175, mask='auto')
        self.drawText(self.W - self.MARGIN, top - 4, 'CERTIFICADO DE CALIBRAÇÃO', BOLD, 17, DEEP, 'right', 0.4)
        self.drawText(self.W - self.MARGIN, top - 19, 'Unidade de referência de movimento · Measure MRU', REGULAR, 9, MUTED, 'right')
        self.drawText(self.W - self.MARGIN, top - 33, f'Nº {self.number}', SEMIBOLD, 9, INK, 'right')

        c.setStrokeColor(PURPLE); c.setLineWidth(0.9)
        c.line(self.MARGIN, top - 44, self.W - self.MARGIN, top - 44)
        return top - 44

    # A MARCA D'ÁGUA POR CIMA DE TUDO, GRÁFICOS INCLUSIVE: A REFERÊNCIA FOI O PRÓPRIO MRU
    def drawWatermark(self):
        c = self.canvas

        c.saveState()
        c.setFillColor(AMBER); c.setFillAlpha(0.09)
        c.translate(self.W/2, self.H/2 - 40); c.rotate(38)
        c.setFont(BOLD, 130); c.drawCentredString(0, -45, 'DEBUG')
        c.restoreState()

    # OS DADOS DO ENSAIO EM DUAS COLUNAS À ESQUERDA E O PARECER À DIREITA, NA MESMA ALTURA
    def drawSummary(self, top):
        c       = self.canvas
        height  = 100
        left    = self.width() * 0.6
        right   = self.width() - left - self.GAP
        x       = self.MARGIN + left + self.GAP
        verdict = self.getVerdict()
        style   = VERDICTS[verdict['key']]
        items   = list(self.info.items())
        half    = (len(items) + 1) // 2

        self.drawText(self.MARGIN, top - 9, 'IDENTIFICAÇÃO', BOLD, 7.5, DEEP, space=0.5)

        for index, (label, value) in enumerate(items):
            column, row = divmod(index, half)
            px, py      = self.MARGIN + column * left/2, top - 26 - row*22
            self.drawText(px, py, label, REGULAR, 7, MUTED)
            self.drawText(px, py - 10, str(value), SEMIBOLD, 9.5, INK)

        c.setFillColor(style['background'])
        c.roundRect(x, top - height, right, height, 4, fill=1, stroke=0)
        c.setFillColor(style['color'])
        c.rect(x, top - height, 2.5, height, fill=1, stroke=0)

        c.circle(x + 25, top - 27, 12, fill=1, stroke=0)
        self.drawMark(x + 25, top - 27, style['mark'], 11, white, 2.2)
        self.drawText(x + 44, top - 25, style['title'], BOLD, 17, style['ink'], space=0.4)
        self.drawText(x + 44, top - 38, f'{verdict["passed"]} de {verdict["total"]} requisitos atendidos', SEMIBOLD, 8.5, INK)
        self.drawLines(x + 14, top - 60, style['text'], REGULAR, 8.5, INK, right - 26, 11)
        return top - height

    # O TÍTULO NUMERADO DO DATASHEET, EM CAIXA ALTA COM O FIO ROXO, E A DESCRIÇÃO DO ENSAIO
    def drawSection(self, top, number, section):
        c = self.canvas

        c.setFillColor(PURPLE)
        c.rect(self.MARGIN, top - 14, 14, 14, fill=1, stroke=0)
        self.drawText(self.MARGIN + 7, top - 10.5, str(number), BOLD, 9.5, white, 'center')
        self.drawText(self.MARGIN + 21, top - 11, section['title'].upper(), BOLD, 11, INK, space=0.3)

        c.setStrokeColor(PURPLE); c.setLineWidth(0.6)
        c.line(self.MARGIN, top - 19, self.W - self.MARGIN, top - 19)
        return self.drawLines(self.MARGIN, top - 30, section['about'], REGULAR, 8.5, MUTED, self.width(), 11) - 1

    # CABEÇALHO ROXO, LINHAS ALTERNADAS E O RESULTADO DE CADA REQUISITO NUMA ETIQUETA COLORIDA
    def drawTable(self, top, section):
        c       = self.canvas
        rows    = self.getRows(section)
        headers = ['Parâmetro', 'Requisito'] + section['columns'] + ['Resultado']
        first   = self.width() * 0.36
        last    = self.width() * 0.16
        middle  = (self.width() - first - last) / (len(headers) - 2)
        widths  = [first] + [middle] * (len(headers) - 2) + [last]
        starts  = [self.MARGIN + sum(widths[:index]) for index in range(len(widths))]
        y       = top

        c.setFillColor(DEEP)
        c.rect(self.MARGIN, y - self.ROW, self.width(), self.ROW, fill=1, stroke=0)

        for index, header in enumerate(headers):
            self.drawText(starts[index] + 6 if index == 0 else starts[index] + widths[index]/2, y - 11, header, SEMIBOLD, 8, white, 'left' if index == 0 else 'center')

        y -= self.ROW

        for line, row in enumerate(rows):
            if line % 2:
                c.setFillColor(ZEBRA)
                c.rect(self.MARGIN, y - self.ROW, self.width(), self.ROW, fill=1, stroke=0)

            cells = [row['limit']] + row['values']
            self.drawText(starts[0] + 6, y - 11, row['label'], REGULAR, 8.5, INK)

            for index, cell in enumerate(cells, start=1):
                self.drawText(starts[index] + widths[index]/2, y - 11, cell, REGULAR, 8.5, MUTED if index == 1 else INK, 'center')

            style = VERDICTS['approved' if row['passed'] else 'failed']
            c.setFillColor(style['background'])
            c.roundRect(starts[-1] + widths[-1]/2 - 31, y - 12.5, 62, 10.5, 5.25, fill=1, stroke=0)
            label = starts[-1] + widths[-1]/2 - (pdfmetrics.stringWidth(style['label'], SEMIBOLD, 7.5) - 9) / 2
            self.drawMark(label - 6, y - 7.6, style['mark'], 6, style['ink'], 1.1)
            self.drawText(label, y - 10.3, style['label'], SEMIBOLD, 7.5, style['ink'])

            c.setStrokeColor(LINE); c.setLineWidth(0.6)
            c.line(self.MARGIN, y - self.ROW, self.W - self.MARGIN, y - self.ROW)
            y -= self.ROW

        return y

    # DETALHE EM MOVIMENTO EM CIMA E ERRO DO ENSAIO INTEIRO EMBAIXO, UM ÂNGULO POR COLUNA, NO TAMANHO EM QUE FORAM DESENHADOS
    def drawPlots(self, top):
        width  = (self.width() - self.GAP) / 2
        height = width * PANEL
        y      = top

        for name in ['ref_vs_model', 'error']:
            for column, axis in enumerate(PLOTTED):
                self.canvas.drawImage(self.plots[f'{axis}_{name}'], self.MARGIN + column*(width + self.GAP), y - height, width=width, height=height, mask='auto')

            y -= height + 6

        return y + 6

    # AS OBSERVAÇÕES À ESQUERDA E A ASSINATURA DO RESPONSÁVEL À DIREITA
    def drawClosing(self, top):
        c     = self.canvas
        left  = self.width() * 0.6
        x     = self.MARGIN + left + 2*self.GAP
        width = self.W - self.MARGIN - x

        self.drawText(self.MARGIN, top - 9, 'OBSERVAÇÕES', BOLD, 7.5, DEEP, space=0.5)
        bottom = self.drawLines(self.MARGIN, top - 22, NOTES, REGULAR, 7.5, MUTED, left, 10)

        c.drawImage(SIGN, x + width/2 - 52, top - 44, width=104, height=32.5, mask='auto')
        c.setStrokeColor(INK); c.setLineWidth(0.5)
        c.line(x, top - 46, x + width, top - 46)
        self.drawText(x + width/2, top - 57, 'Eng. de Calibração', SEMIBOLD, 8.5, INK, 'center')
        self.drawText(x + width/2, top - 67, 'Responsável técnico · Measure Offshore', REGULAR, 7.5, MUTED, 'center')
        return min(bottom, top - 67)

    def drawFooter(self):
        c, y = self.canvas, 12*mm

        c.setStrokeColor(LINE); c.setLineWidth(0.6)
        c.line(self.MARGIN, y + 10, self.W - self.MARGIN, y + 10)
        self.drawText(self.MARGIN, y, 'Measure Offshore · measureoffshore.com', SEMIBOLD, 7.5, DEEP)
        self.drawText(self.W/2, y, f'Certificado {self.number} · emitido em {datetime.datetime.now():%d/%m/%Y %H:%M}', REGULAR, 7.5, MUTED, 'center')
        self.drawText(self.W - self.MARGIN, y, 'Página 1 de 1', REGULAR, 7.5, MUTED, 'right')

    def export(self):
        missing = [axis for axis in PLOTTED if f'{axis}_error' not in self.plots]

        if missing:
            raise ValueError(f'a estratégia não estima {missing}: o certificado precisa de roll e pitch')

        self.canvas = canvas.Canvas(self.output, pagesize=A4, initialFontName=REGULAR)
        self.canvas.setTitle(f'Certificado de calibração {self.number}')
        self.canvas.setAuthor('Measure Offshore')
        self.canvas.setSubject(f'Calibração do MRU · {" · ".join(str(value) for value in self.info.values())}')
        self.canvas.setCreator('MRU Monitor')

        y = self.drawSummary(self.drawHeader() - 16)

        for number, section in enumerate(SECTIONS, start=1):
            y = self.drawSection(y - 24, number, section)
            y = self.drawTable(y - 4, section)

            if section['plots']:
                y = self.drawPlots(y - 10)

        self.drawClosing(y - 26)
        self.drawFooter()

        if self.debug:
            self.drawWatermark()

        self.canvas.save()
        return self.output
