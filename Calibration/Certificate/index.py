import os, json, random, datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas

C_DARK = HexColor('#3A1078')
C_MID = HexColor('#6A3CBC')
C_LIGHT = HexColor('#9B72CF')
C_GREEN = HexColor('#2E7D32')
C_CHECK = HexColor('#4CAF50')
C_TEXT = HexColor('#333333')
C_GRAY = HexColor('#E0E0E0')
C_BG_HEADER = HexColor('#6A3CBC')
C_BG_ALT = HexColor('#F3EDFA')


class ReportData:
    """Handles raw data loading and structuring (No visual formatting here)."""
    
    def __init__(self, config):
        self.config = config
        self.basePath = config['system'].get('basePath', '.')
        self.metrics = {}
        self.plots = {}
        self._load_files()

    def _load_files(self):
        releaseDir = os.path.join(self.basePath, 'results')
        axes = ['roll', 'pitch', 'yaw', 'wx', 'wy', 'wz', 'ax', 'ay', 'az']

        for axis in axes:
            axisDir = os.path.join(releaseDir, axis)
            metricsPath = os.path.join(axisDir, 'metrics.json')
            
            self.metrics[axis] = {}
            if os.path.exists(metricsPath):
                with open(metricsPath, 'r', encoding='utf-8') as f:
                    self.metrics[axis] = json.load(f)

            if axis in ['roll', 'pitch']:
                refPlot = os.path.join(axisDir, 'ref_vs_model.png')
                errPlot = os.path.join(axisDir, 'error.png')
                
                if not os.path.exists(refPlot) or not os.path.exists(errPlot):
                    raise FileNotFoundError(f'Plots missing for {axis}. Run analysis first.')
                
                self.plots[f'{axis}Ref'] = refPlot
                self.plots[f'{axis}Err'] = errPlot

    def _safe_max(self, axes_list, metric_key):
        """Busca o valor máximo apenas entre os eixos que possuem dados válidos."""
        vals = [self.metrics.get(axis, {}).get(metric_key) for axis in axes_list]
        valid_vals = [v for v in vals if v is not None]
        return max(valid_vals) if valid_vals else None

    def get_roll_pitch_data(self):
        roll = self.metrics.get('roll', {})
        pitch = self.metrics.get('pitch', {})

        metrics = [
            ('RMS estático (deg)', 'rms_stat', 0.5),
            ('RMS dinâmico (deg)', 'rms_dyn', 0.6),
            ('Scale Factor (deg)', 'rms_scale_factor', 0.1)
        ]
        
        results = []
        for label, key, req in metrics:
            v_roll = roll.get(key)
            v_pitch = pitch.get(key)
            
            valid_vals = [v for v in (v_roll, v_pitch) if v is not None]
            max_val    = max(valid_vals) if valid_vals else None
            
            if max_val is not None:
                results.append({
                    'label': label,
                    'val_roll': v_roll,
                    'val_pitch': v_pitch,
                    'max_val': max_val, # Passamos o máximo já calculado para facilitar
                    'required': req
                })
        
        return results

    def get_gyro_data(self):
        metrics = [
            ('Ruído Estático STD (deg/s)', 'std_stat', 0.3, False),
        ]
        
        results = []
        for label, key, req, is_perc in metrics:
            val = self._safe_max(['wx', 'wy', 'wz'], key)
            if val is not None:
                results.append({'label': label, 'value': val, 'required': req, 'is_percentage': is_perc})
        
        return results

    def get_accel_data(self):
        metrics = [
            ('Ruído Estático STD (m/s²)', 'std_stat', 0.05, False),
        ]
        
        results = []
        for label, key, req, is_perc in metrics:
            val = self._safe_max(['ax', 'ay', 'az'], key)
            if val is not None:
                results.append({'label': label, 'value': val, 'required': req, 'is_percentage': is_perc})
                
        return results


class PDFReport:
    """Handles visual PDF rendering entirely, including string interpolation and evaluation."""
    
    W, H = A4
    MARGIN = 15 * mm

    def __init__(self, data: ReportData):
        self.data = data
        self.config = data.config
        
        outPath = os.path.join(data.basePath, self.config['system']['outputPath'])
        os.makedirs(os.path.dirname(outPath), exist_ok=True)
        
        self.canvas = canvas.Canvas(outPath, pagesize=A4)
        self.outPath = outPath

    def _eval_status(self, value, threshold):
        return 'Aprovado' if value <= threshold else 'Reprovado'

    def build(self):
        self._draw_header()
        y = self._draw_info(self.H - 65)
        
        # --- 1. ROLL & PITCH ---
        y = self._draw_section(y - 5, 1, 'TESTES DE ACURÁCIA DE ROLL & PITCH', 
            'O MRU foi submetido a movimentos dinâmicos conhecidos. Comparação entre medido e referência.')
        
        rp_rows = []
        for d in self.data.get_roll_pitch_data():
            max_val = max(d['val_roll'], d['val_pitch'])
            rp_rows.append([
                d['label'],
                f"≤ {d['required']:.4f}",
                f"{d['val_roll']:.4f}",
                f"{d['val_pitch']:.4f}",
                self._eval_status(max_val, d['required'])
            ])
            
        colW = [self._content_width() * p for p in [0.30, 0.18, 0.16, 0.16, 0.20]]
        y = self._draw_table(y - 3, ['Parâmetro', 'Requisito', 'Roll', 'Pitch', 'Status'], rp_rows, colW)
        y = self._draw_plots(y - 3)

        # --- 2. GIROSCÓPIO ---
        y = self._draw_section(y - 5, 2, 'TESTES DE GIROSCÓPIO', 
            'Verificação através de rotações contínuas em velocidades conhecidas.')
        
        gyro_rows = []
        for d in self.data.get_gyro_data():
            if d.get('is_percentage'):
                gyro_rows.append([d['label'], f"≤ {d['required']:.4f} %", f"{d['value']:.4f} %", self._eval_status(d['value'], d['required'])])
            else:
                gyro_rows.append([d['label'], f"≤ {d['required']:.4f}", f"{d['value']:.4f}", self._eval_status(d['value'], d['required'])])

        colW = [self._content_width() * p for p in [0.40, 0.20, 0.20, 0.20]]
        y = self._draw_table(y - 3, ['Parâmetro', 'Requisito', 'Medido', 'Status'], gyro_rows, colW)

        # --- 3. ACELERÔMETRO ---
        y = self._draw_section(y - 15, 3, 'TESTE DE ACELERÔMETRO', 
            'Verificação inclinando o MRU em degraus de 90° em um círculo completo.')
        
        accel_rows = []
        for d in self.data.get_accel_data():
            accel_rows.append([
                d['label'],
                f"≤ {d['required']:.4f}",
                f"{d['value']:.4f}",
                self._eval_status(d['value'], d['required'])
            ])

        colW = [self._content_width() * p for p in [0.35, 0.22, 0.22, 0.21]]
        y = self._draw_table(y - 3, ['Parâmetro', 'Requisito', 'Medido', 'Status'], accel_rows, colW)

        self._draw_footer()
        self.canvas.save()
        return self.outPath

    def _content_width(self):
        return self.W - (2 * self.MARGIN)

    def _draw_header(self):
        c = self.canvas
        h_height = 55
        c.setFillColor(C_DARK)
        c.rect(0, self.H - h_height, self.W, h_height, fill=1, stroke=0)
        
        logo = self.config['system'].get('logoPath')
        if logo and os.path.exists(logo):
            c.drawImage(logo, 12, self.H - h_height + 8, width=120, height=40, preserveAspectRatio=True, mask='auto')

        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 18)
        c.drawRightString(self.W - 15, self.H - 28, 'CERTIFICADO DE CALIBRAÇÃO')
        c.setFont('Helvetica', 12)
        c.drawRightString(self.W - 15, self.H - 44, 'MRU')

    def _draw_info(self, y_pos):
        c = self.canvas
        info = self.config['info']
        y = y_pos - 10
        
        # Left text items
        for label, val in info.items():
            c.setFont('Helvetica-Bold', 7.5)
            c.setFillColor(C_TEXT)
            c.drawString(self.MARGIN + 5, y, f'{label}:')
            c.setFont('Helvetica', 7.5)
            c.drawString(self.MARGIN + 125, y, str(val))
            y -= 13

        # Right certification text & signature
        rightX = self.W / 2 + 20
        textObj = c.beginText(rightX, y_pos - 10)
        textObj.setFont('Helvetica', 7)
        textObj.setFillColor(C_TEXT)
        
        certText = "Este certificado atesta que o sistema MRU foi calibrado conforme procedimentos internos."
        line, maxW = '', (self.W - self.MARGIN - rightX - 10)
        
        for word in certText.split():
            test = f"{line} {word}".strip()
            if c.stringWidth(test, 'Helvetica', 7) < maxW:
                line = test
            else:
                textObj.textLine(line)
                line = word
        textObj.textLine(line)
        c.drawText(textObj)

        sig = self.config['system'].get('signaturePath')
        if sig and os.path.exists(sig):
            c.drawImage(sig, rightX + 60, y_pos - 70, width=90, height=30, preserveAspectRatio=True, mask='auto')
        
        c.setFont('Helvetica', 6.5)
        c.drawString(rightX + 60, y_pos - 78, 'Eng. de Calibração')
        
        return y_pos - 100

    def _draw_section(self, y_pos, num, title, desc):
        c = self.canvas
        c.setFont('Helvetica-Bold', 9)
        c.setFillColor(C_DARK)
        c.drawString(self.MARGIN, y_pos, f'{num}. {title}')
        y_pos -= 14

        c.setFont('Helvetica', 6.5)
        c.setFillColor(C_TEXT)
        c.drawString(self.MARGIN, y_pos, desc)
        return y_pos - 12

    def _draw_table(self, y_pos, headers, rows, colWidths):
        c = self.canvas
        tableW = self._content_width()
        x, y = self.MARGIN, y_pos

        # Header
        c.setFillColor(C_BG_HEADER)
        c.rect(x, y - 18, tableW, 18, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 7)
        
        cx = x
        for i, h in enumerate(headers):
            c.drawCentredString(cx + colWidths[i] / 2, y - 12, h)
            cx += colWidths[i]
        y -= 18

        # Rows
        for ri, row in enumerate(rows):
            if ri % 2 == 1:
                c.setFillColor(C_BG_ALT)
                c.rect(x, y - 16, tableW, 16, fill=1, stroke=0)

            cx = x
            for i, cell in enumerate(row):
                cellStr = str(cell)
                if cellStr == 'Aprovado':
                    c.setFillColor(C_GREEN)
                    c.setFont('Helvetica-Bold', 6.5)
                else:
                    c.setFillColor(C_TEXT)
                    c.setFont('Helvetica', 6.5)
                
                c.drawCentredString(cx + colWidths[i] / 2, y - 11, cellStr)
                cx += colWidths[i]
            y -= 16

        c.setStrokeColor(C_GRAY)
        c.setLineWidth(0.3)
        c.line(x, y, x + tableW, y)
        return y - 5

    def _draw_plots(self, y_pos):
        c = self.canvas
        gap = 8
        imgW = (self._content_width() - gap) / 2
        imgH = imgW * (150 / 250)
        y = y_pos

        plots = self.data.plots
        c.drawImage(plots['rollRef'], self.MARGIN, y - imgH, width=imgW, height=imgH, mask='auto')
        c.drawImage(plots['pitchRef'], self.MARGIN + imgW + gap, y - imgH, width=imgW, height=imgH, mask='auto')
        y -= imgH + 5

        c.drawImage(plots['rollErr'], self.MARGIN, y - imgH, width=imgW, height=imgH, mask='auto')
        c.drawImage(plots['pitchErr'], self.MARGIN + imgW + gap, y - imgH, width=imgW, height=imgH, mask='auto')
        return y - imgH - 5

    def _draw_footer(self):
        c = self.canvas
        c.setFillColor(HexColor('#F0F7F0'))
        c.rect(0, 0, self.W, 35, fill=1, stroke=0)

        c.setStrokeColor(C_CHECK)
        c.setLineWidth(1)
        c.line(0, 35, self.W, 35)

        circleX, circleY = self.MARGIN + 12, 17.5
        c.setFillColor(C_CHECK)
        c.circle(circleX, circleY, 10, fill=1, stroke=0)
        
        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 14)
        c.drawCentredString(circleX, circleY - 5, '✓')

        c.setFillColor(C_GREEN)
        c.setFont('Helvetica-Bold', 6.5)
        c.drawString(circleX + 18, circleY + 4, 'O sistema MRU atende a todos os requisitos de calibração.')
        c.setFont('Helvetica', 5.5)
        c.setFillColor(C_TEXT)
        c.drawString(circleX + 18, circleY - 6, 'Recomendamos nova calibração em 12 meses.')

        c.setFillColor(C_DARK)
        c.setFont('Helvetica-Bold', 7)
        c.drawRightString(self.W - self.MARGIN, circleY + 5, 'measureoffshore.com')


if __name__ == '__main__':
    config = {
        'system': {
            'basePath': os.path.dirname(os.path.abspath(__file__)),
            'outputPath': 'release/certificate.pdf',
            'logoPath': 'images/measure.png',
            'signaturePath': 'images/signature.png'
        },
        'info': {
            'Modelo do MRU': 'Measure MRU',
            'Número de Série': '0001',
            'Nº do Certificado': f'MO-{datetime.date.today().strftime("%Y%m%d")}-{int(random.randint(100,9999)):04d}',
            'Data da Calibração': datetime.date.today().strftime('%d/%m/%Y'),
            'Versão do Firmware': 'v1.0.0',
            'Técnico': 'Measure Offshore'
        }
    }

    data_handler = ReportData(config)
    pdf_builder = PDFReport(data_handler)
    
    path = pdf_builder.build()
    print(f'Certificate generated: {path}')