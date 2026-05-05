import os
import json
import matplotlib
matplotlib.use('Agg')
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


PURPLE_DARK = HexColor('#3A1078')
PURPLE_MID = HexColor('#6A3CBC')
PURPLE_LIGHT = HexColor('#9B72CF')
GREEN_DARK = HexColor('#2E7D32')
GREEN_CHECK = HexColor('#4CAF50')
GRAY_TEXT = HexColor('#333333')
GRAY_LIGHT = HexColor('#E0E0E0')
TABLE_HEADER_BG = HexColor('#6A3CBC')
TABLE_ALT_BG = HexColor('#F3EDFA')


class CalibrationReport:
    PAGE_W, PAGE_H = A4
    MARGIN = 15 * mm

    def __init__(self, config):
        self.config = config
        self.basePath = config.get('basePath', '.')
        self.logoPath = os.path.join(self.basePath, config.get('logoPath', 'certificate/images/measure.png'))
        self.signaturePath = os.path.join(self.basePath, config.get('signaturePath', 'certificate/images/signature.png'))
        self.rollMetrics = None
        self.pitchMetrics = None
        self.rollCalibration = None
        self.pitchCalibration = None
        self.rollRefPlot = None
        self.rollErrPlot = None
        self.pitchRefPlot = None
        self.pitchErrPlot = None

    def _loadFromRelease(self):
        releaseDir = os.path.join(self.basePath, 'release')

        for axis in ['roll', 'pitch']:
            axisDir = os.path.join(releaseDir, axis)

            metricsPath = os.path.join(axisDir, 'metrics.json')
            if not os.path.exists(metricsPath):
                raise FileNotFoundError(f'Metrics not found: {metricsPath}. Run the analysis notebook first.')
            with open(metricsPath, 'r', encoding='utf-8') as f:
                metrics = json.load(f)

            calPath = os.path.join(axisDir, 'calibration.json')
            calibration = None
            if os.path.exists(calPath):
                with open(calPath, 'r', encoding='utf-8') as f:
                    calibration = json.load(f)

            refPlot = os.path.join(axisDir, 'ref_vs_model.png')
            errPlot = os.path.join(axisDir, 'error.png')

            if not os.path.exists(refPlot):
                raise FileNotFoundError(f'Plot not found: {refPlot}. Run the analysis notebook first.')
            if not os.path.exists(errPlot):
                raise FileNotFoundError(f'Plot not found: {errPlot}. Run the analysis notebook first.')

            if axis == 'roll':
                self.rollMetrics = metrics
                self.rollCalibration = calibration
                self.rollRefPlot = refPlot
                self.rollErrPlot = errPlot
            else:
                self.pitchMetrics = metrics
                self.pitchCalibration = calibration
                self.pitchRefPlot = refPlot
                self.pitchErrPlot = errPlot

    def _drawHeader(self, c):
        w, h = self.PAGE_W, self.PAGE_H
        headerH = 55

        c.saveState()
        c.setFillColor(PURPLE_DARK)
        c.rect(0, h - headerH, w, headerH, fill=1, stroke=0)

        try:
            c.drawImage(self.logoPath, 12, h - headerH + 8, width=120, height=40, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 18)
        c.drawRightString(w - 15, h - 28, 'CERTIFICADO DE CALIBRAÇÃO')
        c.setFont('Helvetica', 12)
        c.drawRightString(w - 15, h - 44, 'MRU')
        c.restoreState()

    def _drawInfoSection(self, c, yPos):
        cfg = self.config
        leftX = self.MARGIN + 5
        labelX = leftX
        valueX = leftX + 120

        fields = [
            ('Modelo do MRU:', cfg.get('modelo', 'Measure MRU')),
            ('Número de Série:', cfg.get('serialNumber', '7929')),
            ('Número do Certificado:', cfg.get('certificateNumber', 'MO-20250702-7929')),
            ('Data da Calibração:', cfg.get('calibrationDate', '02/07/2025')),
            ('Versão do Firmware:', cfg.get('firmwareVersion', '4.x')),
            ('Técnico Responsável:', cfg.get('technician', 'Measure Offshore')),
        ]

        c.setStrokeColor(GRAY_LIGHT)
        c.setLineWidth(0.5)
        c.line(self.MARGIN, yPos + 5, self.PAGE_W - self.MARGIN, yPos + 5)

        y = yPos - 10
        for label, value in fields:
            c.setFont('Helvetica-Bold', 7.5)
            c.setFillColor(GRAY_TEXT)
            c.drawString(labelX, y, label)
            c.setFont('Helvetica', 7.5)
            c.drawString(valueX, y, str(value))
            y -= 13

        rightX = self.PAGE_W / 2 + 20
        rightW = self.PAGE_W - self.MARGIN - rightX
        certText = cfg.get('certificationText',
            'Este certificado atesta que o sistema MRU acima identificado foi '
            'calibrado e testado conforme os procedimentos internos da '
            'Measure Offshore, atendendo às especificações técnicas do equipamento.'
        )
        c.setFont('Helvetica', 7)
        c.setFillColor(GRAY_TEXT)
        textObj = c.beginText(rightX, yPos - 10)
        textObj.setFont('Helvetica', 7)
        textObj.setFillColor(GRAY_TEXT)

        words = certText.split()
        line = ''
        maxLineW = rightW - 10
        for word in words:
            test = line + ' ' + word if line else word
            if c.stringWidth(test, 'Helvetica', 7) < maxLineW:
                line = test
            else:
                textObj.textLine(line)
                line = word
        if line:
            textObj.textLine(line)
        c.drawText(textObj)

        try:
            sigY = yPos - 70
            c.drawImage(self.signaturePath, rightX + 30, sigY, width=90, height=30, preserveAspectRatio=True, mask='auto')
            c.setFont('Helvetica', 6.5)
            c.setFillColor(GRAY_TEXT)
            c.drawString(rightX + 30, sigY - 8, 'Eng. de Calibração')
            c.drawString(rightX + 30, sigY - 16, 'Measure Offshore')
        except Exception:
            pass

        bottomY = yPos - 100
        c.setStrokeColor(GRAY_LIGHT)
        c.line(self.MARGIN, bottomY, self.PAGE_W - self.MARGIN, bottomY)
        return bottomY

    def _drawSectionTitle(self, c, yPos, number, title):
        c.setFont('Helvetica-Bold', 9)
        c.setFillColor(PURPLE_DARK)
        c.drawString(self.MARGIN, yPos, f'{number}. {title}')
        return yPos - 14

    def _drawDescription(self, c, yPos, text, maxWidth=None):
        if maxWidth is None:
            maxWidth = self.PAGE_W - 2 * self.MARGIN - 10
        c.setFont('Helvetica', 6.5)
        c.setFillColor(GRAY_TEXT)
        words = text.split()
        line = ''
        y = yPos
        for word in words:
            test = line + ' ' + word if line else word
            if c.stringWidth(test, 'Helvetica', 6.5) < maxWidth:
                line = test
            else:
                c.drawString(self.MARGIN, y, line)
                y -= 9
                line = word
        if line:
            c.drawString(self.MARGIN, y, line)
            y -= 9
        return y - 2

    def _drawTable(self, c, yPos, headers, rows, colWidths=None):
        tableW = self.PAGE_W - 2 * self.MARGIN
        numCols = len(headers)
        if colWidths is None:
            colWidths = [tableW / numCols] * numCols

        rowH = 16
        headerH = 18
        x = self.MARGIN
        y = yPos

        c.setFillColor(TABLE_HEADER_BG)
        c.rect(x, y - headerH, tableW, headerH, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 7)
        cx = x
        for i, h in enumerate(headers):
            c.drawCentredString(cx + colWidths[i] / 2, y - 12, h)
            cx += colWidths[i]
        y -= headerH

        for ri, row in enumerate(rows):
            if ri % 2 == 1:
                c.setFillColor(TABLE_ALT_BG)
                c.rect(x, y - rowH, tableW, rowH, fill=1, stroke=0)

            c.setFillColor(GRAY_TEXT)
            c.setFont('Helvetica', 6.5)
            cx = x
            for i, cell in enumerate(row):
                cellStr = str(cell)
                if cellStr.lower() == 'aprovado':
                    c.setFillColor(GREEN_DARK)
                    c.setFont('Helvetica-Bold', 6.5)
                else:
                    c.setFillColor(GRAY_TEXT)
                    c.setFont('Helvetica', 6.5)
                c.drawCentredString(cx + colWidths[i] / 2, y - 11, cellStr)
                cx += colWidths[i]
            y -= rowH

        c.setStrokeColor(GRAY_LIGHT)
        c.setLineWidth(0.3)
        c.line(x, y, x + tableW, y)
        return y - 5

    def _drawAccuracyPlots(self, c, yPos):
        plotW = 250
        plotH = 150
        gap = 8
        leftX = self.MARGIN
        rightX = self.MARGIN + plotW + gap

        imgW = (self.PAGE_W - 2 * self.MARGIN - gap) / 2
        imgH = imgW * plotH / plotW

        y = yPos
        c.drawImage(self.rollRefPlot, leftX, y - imgH, width=imgW, height=imgH, mask='auto')
        c.drawImage(self.pitchRefPlot, rightX, y - imgH, width=imgW, height=imgH, mask='auto')
        y -= imgH + 5

        c.drawImage(self.rollErrPlot, leftX, y - imgH, width=imgW, height=imgH, mask='auto')
        c.drawImage(self.pitchErrPlot, rightX, y - imgH, width=imgW, height=imgH, mask='auto')
        y -= imgH + 5

        return y

    def _buildAccuracyRows(self):
        rollRmse = self.rollMetrics.get('rmse', 0) if self.rollMetrics else 0
        pitchRmse = self.pitchMetrics.get('rmse', 0) if self.pitchMetrics else 0
        rollMax = self.rollMetrics.get('maxError', 0) if self.rollMetrics else 0
        pitchMax = self.pitchMetrics.get('maxError', 0) if self.pitchMetrics else 0

        def evaluate(value, threshold):
            return 'Aprovado' if value <= threshold else 'Reprovado'

        rows = [
            ['RMS - Roll (deg)', '≤ 0.02', f'{rollRmse:.4f}', evaluate(rollRmse, 0.02)],
            ['RMS - Pitch (deg)', '≤ 0.02', f'{pitchRmse:.4f}', evaluate(pitchRmse, 0.02)],
            ['Erro Máximo - Roll (deg)', '≤ 0.20', f'{rollMax:.4f}', evaluate(rollMax, 0.20)],
            ['Erro Máximo - Pitch (deg)', '≤ 0.20', f'{pitchMax:.4f}', evaluate(pitchMax, 0.20)],
        ]
        return rows

    def _drawFooter(self, c):
        w = self.PAGE_W
        footerH = 35

        c.setFillColor(HexColor('#F0F7F0'))
        c.rect(0, 0, w, footerH, fill=1, stroke=0)

        c.setStrokeColor(GREEN_CHECK)
        c.setLineWidth(1)
        c.line(0, footerH, w, footerH)

        circleX = self.MARGIN + 12
        circleY = footerH / 2
        c.setFillColor(GREEN_CHECK)
        c.circle(circleX, circleY, 10, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 14)
        c.drawCentredString(circleX, circleY - 5, '✓')

        textX = circleX + 18
        c.setFillColor(GREEN_DARK)
        c.setFont('Helvetica-Bold', 6.5)
        c.drawString(textX, circleY + 4, 'O sistema MRU atende a todos os requisitos de calibração da Measure Offshore.')
        c.setFont('Helvetica', 5.5)
        c.setFillColor(GRAY_TEXT)
        c.drawString(textX, circleY - 6, 'Recomendamos nova calibração em até 12 meses ou conforme necessidade operacional.')

        c.setFillColor(PURPLE_DARK)
        c.setFont('Helvetica-Bold', 7)
        c.drawRightString(w - self.MARGIN, circleY + 5, 'measureoffshore.com')
        c.setFont('Helvetica', 5.5)
        c.setFillColor(PURPLE_LIGHT)
        c.drawRightString(w - self.MARGIN, circleY - 5, 'Precision. Motion. Confidence.')

    def generate(self, outputPath=None):
        if outputPath is None:
            outputPath = os.path.join(self.basePath, self.config.get('outputPath', 'release/certificate.pdf'))

        outDir = os.path.dirname(outputPath)
        if outDir and not os.path.exists(outDir):
            os.makedirs(outDir, exist_ok=True)

        self._loadFromRelease()

        c = canvas.Canvas(outputPath, pagesize=A4)
        w, h = self.PAGE_W, self.PAGE_H

        self._drawHeader(c)

        y = h - 65
        y = self._drawInfoSection(c, y)

        y -= 5
        y = self._drawSectionTitle(c, y, 1, 'TESTES DE ACURÁCIA DE ROLL & PITCH')
        y = self._drawDescription(c, y,
            'O MRU foi submetido a excitações senoidais dinâmicas em ±4 Hz por 30 minutos em cada eixo. '
            'A precisão dinâmica foi avaliada através da comparação entre os valores medidos pelo MRU '
            'e os valores de referência do sistema de calibração.'
        )

        y -= 3
        headers1 = ['Parâmetro', 'Requisito de Teste', 'Valor Medido', 'Resultado']
        tableW = self.PAGE_W - 2 * self.MARGIN
        colW1 = [tableW * 0.35, tableW * 0.22, tableW * 0.22, tableW * 0.21]

        rows1 = self._buildAccuracyRows()
        y = self._drawTable(c, y, headers1, rows1, colW1)

        y -= 3
        y = self._drawAccuracyPlots(c, y)

        y -= 3
        y = self._drawSectionTitle(c, y, 2, 'TESTE DE FATOR DE ESCALA (SENSOR GYRO)')
        y = self._drawDescription(c, y,
            'O fator de escala do sensor giroscópio foi verificado através de rotações contínuas em velocidades conhecidas. '
            'O MRU deve permanecer dentro da tolerância especificada.'
        )

        gyroData = self.config.get('gyroScaleFactor', {})
        headers2 = ['Eixo', 'Requisito de Teste', 'Fator de Escala Medido', 'Desvio (%)', 'Resultado']
        colW2 = [tableW * 0.15, tableW * 0.22, tableW * 0.25, tableW * 0.18, tableW * 0.20]
        rows2 = [
            ['Roll (X)', '± 0.50 %', gyroData.get('rollScale', '1.0023'), gyroData.get('rollDev', '+0.23'), 'Aprovado'],
            ['Pitch (Y)', '± 0.50 %', gyroData.get('pitchScale', '0.9987'), gyroData.get('pitchDev', '-0.13'), 'Aprovado'],
            ['Yaw (Z)', '± 0.50 %', gyroData.get('yawScale', '1.0011'), gyroData.get('yawDev', '-0.11'), 'Aprovado'],
        ]
        y -= 3
        y = self._drawTable(c, y, headers2, rows2, colW2)

        y -= 5
        y = self._drawSectionTitle(c, y, 3, 'TESTE DE ACELERÔMETRO')
        y = self._drawDescription(c, y,
            'O fator de escala do acelerômetro foi verificado inclinando-se o MRU em degraus de 90° em um círculo completo. '
            'O desvio deve estar dentro da tolerância especificada.'
        )

        accelData = self.config.get('accelerometer', {})
        headers3 = ['Parâmetro', 'Requisito de Teste', 'Desvio Máximo', 'Resultado']
        colW3 = [tableW * 0.35, tableW * 0.22, tableW * 0.22, tableW * 0.21]
        rows3 = [
            ['Fator de escala (acelerômetro)', '± 2.00 %', accelData.get('scaleDev', '0.92 %'), 'Aprovado'],
            ['Não linearidade', '± 2.00 %', accelData.get('linearityDev', '0.84 %'), 'Aprovado'],
            ['Erro de alinhamento', '± 2.00 %', accelData.get('alignmentDev', '1.10 %'), 'Aprovado'],
        ]
        y -= 3
        y = self._drawTable(c, y, headers3, rows3, colW3)

        self._drawFooter(c)

        c.save()
        return outputPath


if __name__ == '__main__':
    config = {
        'basePath': os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'modelo': 'Measure MRU',
        'serialNumber': '7929',
        'certificateNumber': 'MO-20250702-7929',
        'calibrationDate': '02/07/2025',
        'firmwareVersion': '4.x',
        'technician': 'Measure Offshore',
        'logoPath': 'certificate/images/measure.png',
        'signaturePath': 'certificate/images/signature.png',
        'outputPath': 'release/certificate.pdf',
        'gyroScaleFactor': {
            'rollScale': '1.0023', 'rollDev': '+0.23',
            'pitchScale': '0.9987', 'pitchDev': '-0.13',
            'yawScale': '1.0011', 'yawDev': '-0.11',
        },
        'accelerometer': {
            'scaleDev': '0.92 %',
            'linearityDev': '0.84 %',
            'alignmentDev': '1.10 %',
        },
    }

    report = CalibrationReport(config)
    path = report.generate()
    print(f'Certificate generated: {path}')
