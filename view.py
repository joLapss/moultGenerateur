from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QSlider, QComboBox, QPushButton, QCheckBox, 
                             QGroupBox, QSizePolicy, QTabWidget, QDoubleSpinBox, QScrollArea)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QPolygonF, QFont
import numpy as np


class WaveformDrawer(QWidget):
    waveformChanged = pyqtSignal(np.ndarray)

    def __init__(self, num_points=512, is_unipolar=False, mode_type='bipolar', line_color=(0, 255, 100), parent=None):
        super().__init__(parent)
        self.num_points = num_points
        self.is_unipolar = is_unipolar
        self.mode_type = mode_type
        self.line_color = line_color
        self.freq_min = 100.0
        self.freq_max = 1000.0
        
        default_val = 1.0 if self.mode_type == 'volume' else (0.5 if self.is_unipolar else 0.0)
        self.waveform_data = np.full(self.num_points, default_val, dtype=np.float32)
        
        self.setCursor(Qt.CrossCursor)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.is_drawing = False
        self.last_mouse_pos = None

    def set_frequency_bounds(self, fmin, fmax):
        self.freq_min = float(fmin)
        self.freq_max = float(fmax)
        self.update()

    def reset_waveform(self):
        default_val = 1.0 if self.mode_type == 'volume' else (0.5 if self.is_unipolar else 0.0)
        self.waveform_data = np.full(self.num_points, default_val, dtype=np.float32)
        self.update()
        self.waveformChanged.emit(self.waveform_data)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width, height = self.width(), self.height()

        painter.fillRect(self.rect(), QColor(30, 30, 30))
        painter.setPen(QPen(QColor(70, 70, 70), 1, Qt.DashLine))

        if self.is_unipolar:
            y_top, y_mid, y_bot = height * 0.1, height / 2.0, height * 0.9
            painter.drawLine(0, int(y_top), width, int(y_top))
            painter.drawLine(0, int(y_mid), width, int(y_mid))
            painter.drawLine(0, int(y_bot), width, int(y_bot))

            for pct in [0.25, 0.5, 0.75]:
                painter.drawLine(int(width * pct), 0, int(width * pct), height)

            painter.setFont(QFont("Arial", 8, QFont.Bold))
            painter.setPen(QColor(230, 230, 230))

            if self.mode_type == 'freq':
                f_mid = (self.freq_min + self.freq_max) / 2.0
                painter.drawText(8, int(y_top) - 4, f"Max: {self.freq_max:.1f} Hz")
                painter.drawText(8, int(y_mid) - 4, f"Mid: {f_mid:.1f} Hz")
                painter.drawText(8, int(y_bot) + 14, f"Min: {self.freq_min:.1f} Hz")
            elif self.mode_type == 'volume':
                painter.drawText(8, int(y_top) - 4, "100%")
                painter.drawText(8, int(y_mid) - 4, "50%")
                painter.drawText(8, int(y_bot) + 14, "0%")
        else:
            painter.drawLine(0, int(height/2), width, int(height/2))

        painter.setPen(QPen(QColor(*self.line_color), 2))
        polygon = QPolygonF()
        x_step = width / (self.num_points - 1)
        
        for i in range(self.num_points):
            x = i * x_step
            if self.is_unipolar:
                y = height * 0.9 - (self.waveform_data[i] * height * 0.8)
            else:
                y = (height / 2) - (self.waveform_data[i] * (height / 2) * 0.9)
            polygon.append(QPoint(int(x), int(y)))
        
        painter.drawPolyline(polygon)

    def _pos_to_val(self, pos_y):
        height = self.height()
        if self.is_unipolar:
            return max(0.0, min((height * 0.9 - pos_y) / (height * 0.8), 1.0))
        else:
            return max(-1.0, min(((height / 2.0) - pos_y) / ((height / 2.0) * 0.9), 1.0))

    def _apply_continuous_stroke(self, current_pos):
        width = self.width()
        if self.last_mouse_pos is None:
            self.last_mouse_pos = current_pos

        x0, y0 = self.last_mouse_pos.x(), self.last_mouse_pos.y()
        x1, y1 = current_pos.x(), current_pos.y()

        idx0 = max(0, min(int((x0 / width) * self.num_points), self.num_points - 1))
        idx1 = max(0, min(int((x1 / width) * self.num_points), self.num_points - 1))
        start_idx, end_idx = min(idx0, idx1), max(idx0, idx1)

        if start_idx == end_idx:
            self.waveform_data[start_idx] = self._pos_to_val(y1)
        else:
            for i in range(start_idx, end_idx + 1):
                t = (i - idx0) / (idx1 - idx0) if idx1 != idx0 else 0
                y_interp = y0 + t * (y1 - y0)
                self.waveform_data[i] = self._pos_to_val(y_interp)

        self.last_mouse_pos = current_pos
        self.update()
        self.waveformChanged.emit(self.waveform_data)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_drawing = True
            self.last_mouse_pos = event.pos()
            self._apply_continuous_stroke(event.pos())

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            self._apply_continuous_stroke(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_drawing = False
            self.last_mouse_pos = None


class OscillatorWidget(QWidget):
    def __init__(self, osc_index, parent=None):
        super().__init__(parent)
        self.osc_index = osc_index
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. Choix Forme d'onde
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Forme d'Onde :"))
        self.combo_wave = QComboBox()
        self.combo_wave.addItems([
            "Sinus", 
            "Carré", 
            "Triangle", 
            "Dent de scie", 
            "Tangente", 
            "Bruit Blanc (Noise)", 
            "Dessinée (Custom)"
        ])
        h1.addWidget(self.combo_wave)
        self.btn_reset_wave = QPushButton("Réinit Onde")
        h1.addWidget(self.btn_reset_wave)
        layout.addLayout(h1)

        self.wave_drawer = WaveformDrawer(num_points=512, is_unipolar=False, mode_type='bipolar', line_color=(0, 255, 100))
        layout.addWidget(self.wave_drawer)

        # 2. Entrée Audio
        audio_mod_group = QGroupBox("Automatisation par l'Entrée Audio (Micro/Ligne)")
        am_layout = QHBoxLayout()
        am_layout.addWidget(QLabel("Contrôler :"))
        self.combo_audio_mod = QComboBox()
        self.combo_audio_mod.addItems(["Désactivé", "Fréquence", "Volume", "Fréquence + Volume"])
        am_layout.addWidget(self.combo_audio_mod)

        am_layout.addWidget(QLabel("Sensibilité :"))
        self.spin_audio_sens = QDoubleSpinBox()
        self.spin_audio_sens.setRange(0.1, 10.0)
        self.spin_audio_sens.setValue(1.0)
        self.spin_audio_sens.setSingleStep(0.1)
        am_layout.addWidget(self.spin_audio_sens)

        audio_mod_group.setLayout(am_layout)
        layout.addWidget(audio_mod_group)

        # 3. Fréquence Fixe
        fixed_group = QGroupBox("Mode Fréquence Fixe")
        f_layout = QVBoxLayout()
        fh = QHBoxLayout()
        fh.addWidget(QLabel("Fréquence :"))
        self.spin_fixed_freq = QDoubleSpinBox()
        self.spin_fixed_freq.setRange(20.0, 20000.0)
        self.spin_fixed_freq.setValue(440.0)
        self.spin_fixed_freq.setSuffix(" Hz")
        self.spin_fixed_freq.setDecimals(1)
        fh.addWidget(self.spin_fixed_freq)
        f_layout.addLayout(fh)

        self.slider_fixed_freq = QSlider(Qt.Horizontal)
        self.slider_fixed_freq.setRange(20, 20000)
        self.slider_fixed_freq.setValue(440)
        f_layout.addWidget(self.slider_fixed_freq)
        fixed_group.setLayout(f_layout)
        layout.addWidget(fixed_group)

        # 4. Asservissement Fréquence (Hz) - Durée jusqu'à 60s
        sweep_group = QGroupBox("Balayage de Fréquence (Hz)")
        sw_layout = QVBoxLayout()
        sh = QHBoxLayout()
        self.chk_freq_mod = QCheckBox("Activer l'automatisation fréquence")
        sh.addWidget(self.chk_freq_mod)
        self.btn_reset_freq = QPushButton("Réinit Courbe Fréq")
        sh.addWidget(self.btn_reset_freq)
        sw_layout.addLayout(sh)

        self.freq_drawer = WaveformDrawer(num_points=512, is_unipolar=True, mode_type='freq', line_color=(255, 150, 0))
        sw_layout.addWidget(self.freq_drawer)

        speed_h = QHBoxLayout()
        speed_h.addWidget(QLabel("Vitesse (Durée) :"))
        self.spin_speed = QDoubleSpinBox()
        self.spin_speed.setRange(0.1, 60.0)  # Modifié à 60.0 secondes
        self.spin_speed.setValue(2.0)
        self.spin_speed.setSingleStep(0.5)
        self.spin_speed.setSuffix(" s")
        speed_h.addWidget(self.spin_speed)

        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(1, 600)  # Modifié pour aller jusqu'à 600 (60.0s x 10)
        self.slider_speed.setValue(20)
        speed_h.addWidget(self.slider_speed)
        sw_layout.addLayout(speed_h)

        bounds_h = QHBoxLayout()
        bounds_h.addWidget(QLabel("Min :"))
        self.spin_fmin = QDoubleSpinBox()
        self.spin_fmin.setRange(20.0, 20000.0)
        self.spin_fmin.setValue(100.0)
        self.spin_fmin.setSuffix(" Hz")
        bounds_h.addWidget(self.spin_fmin)

        self.slider_fmin = QSlider(Qt.Horizontal)
        self.slider_fmin.setRange(20, 20000)
        self.slider_fmin.setValue(100)
        bounds_h.addWidget(self.slider_fmin)

        bounds_h.addWidget(QLabel("Max :"))
        self.spin_fmax = QDoubleSpinBox()
        self.spin_fmax.setRange(20.0, 20000.0)
        self.spin_fmax.setValue(1000.0)
        self.spin_fmax.setSuffix(" Hz")
        bounds_h.addWidget(self.spin_fmax)

        self.slider_fmax = QSlider(Qt.Horizontal)
        self.slider_fmax.setRange(20, 20000)
        self.slider_fmax.setValue(1000)
        bounds_h.addWidget(self.slider_fmax)
        
        sw_layout.addLayout(bounds_h)
        sweep_group.setLayout(sw_layout)
        layout.addWidget(sweep_group)

        # 5. Asservissement Volume (%) - Durée jusqu'à 60s
        vol_sweep_group = QGroupBox("Modulateur de Volume (%)")
        vol_sw_layout = QVBoxLayout()
        v_sh = QHBoxLayout()
        self.chk_vol_mod = QCheckBox("Activer le moduleur de volume")
        v_sh.addWidget(self.chk_vol_mod)
        self.btn_reset_vol = QPushButton("Réinit Courbe Vol")
        v_sh.addWidget(self.btn_reset_vol)
        vol_sw_layout.addLayout(v_sh)

        self.vol_drawer = WaveformDrawer(num_points=512, is_unipolar=True, mode_type='volume', line_color=(0, 200, 255))
        vol_sw_layout.addWidget(self.vol_drawer)

        v_speed_h = QHBoxLayout()
        v_speed_h.addWidget(QLabel("Vitesse (Durée) :"))
        self.spin_vol_speed = QDoubleSpinBox()
        self.spin_vol_speed.setRange(0.1, 60.0)  # Modifié à 60.0 secondes
        self.spin_vol_speed.setValue(2.0)
        self.spin_vol_speed.setSingleStep(0.5)
        self.spin_vol_speed.setSuffix(" s")
        v_speed_h.addWidget(self.spin_vol_speed)

        self.slider_vol_speed = QSlider(Qt.Horizontal)
        self.slider_vol_speed.setRange(1, 600)  # Modifié pour aller jusqu'à 600 (60.0s x 10)
        self.slider_vol_speed.setValue(20)
        v_speed_h.addWidget(self.slider_vol_speed)
        vol_sw_layout.addLayout(v_speed_h)

        vol_sweep_group.setLayout(vol_sw_layout)
        layout.addWidget(vol_sweep_group)


class MixerChannelWidget(QWidget):
    def __init__(self, osc_index, parent=None):
        super().__init__(parent)
        self.osc_index = osc_index
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        lbl_title = QLabel(f"<b>OSC {self.osc_index + 1}</b>")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        self.chk_enable = QCheckBox("Actif")
        self.chk_enable.setChecked(False)
        layout.addWidget(self.chk_enable)

        self.combo_channel = QComboBox()
        self.combo_channel.addItems(["L", "R", "L+R"])
        self.combo_channel.setCurrentIndex(2)
        layout.addWidget(self.combo_channel)

        self.slider_amp = QSlider(Qt.Vertical)
        self.slider_amp.setRange(0, 100)
        self.slider_amp.setValue(10)
        self.slider_amp.setMinimumHeight(100)
        layout.addWidget(self.slider_amp, alignment=Qt.AlignHCenter)

        self.lbl_vol = QLabel("10%")
        self.lbl_vol.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_vol)


class SignalGeneratorView(QMainWindow):
    midiSignal = pyqtSignal(int, str, float)

    def __init__(self, num_oscillators=10):
        super().__init__()
        self.num_oscillators = num_oscillators
        self.osc_widgets = []
        self.mixer_widgets = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Générateur de niaisage ({self.num_oscillators}x Oscillateurs)")
        self.setMinimumSize(850, 950)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Sortie Audio :"))
        self.combo_out_device = QComboBox()
        top_layout.addWidget(self.combo_out_device)

        top_layout.addWidget(QLabel("Entrée Audio :"))
        self.combo_in_device = QComboBox()
        top_layout.addWidget(self.combo_in_device)

        top_layout.addWidget(QLabel("MIDI USB :"))
        self.combo_midi = QComboBox()
        top_layout.addWidget(self.combo_midi)
        main_layout.addLayout(top_layout)

        self.tabs = QTabWidget()
        for i in range(self.num_oscillators):
            osc_w = OscillatorWidget(osc_index=i)
            osc_scroll = QScrollArea()
            osc_scroll.setWidgetResizable(True)
            osc_scroll.setWidget(osc_w)
            
            self.osc_widgets.append(osc_w)
            self.tabs.addTab(osc_scroll, f"OSC {i + 1}")
        main_layout.addWidget(self.tabs)

        mixer_group = QGroupBox("Mix Global")
        mixer_group_layout = QVBoxLayout(mixer_group)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_widget = QWidget()
        mixer_layout = QHBoxLayout(scroll_widget)

        for i in range(self.num_oscillators):
            mix_w = MixerChannelWidget(osc_index=i)
            self.mixer_widgets.append(mix_w)
            mixer_layout.addWidget(mix_w)

        scroll_area.setWidget(scroll_widget)
        mixer_group_layout.addWidget(scroll_area)
        main_layout.addWidget(mixer_group)

        self.btn_toggle = QPushButton("Go")
        self.btn_toggle.setStyleSheet("font-weight: bold; padding: 12px; font-size: 14px;")
        main_layout.addWidget(self.btn_toggle)

    def populate_devices(self, out_devices, in_devices, midi_ports):
        self.combo_out_device.clear()
        for idx, name in out_devices:
            self.combo_out_device.addItem(f"[{idx}] {name}", userData=idx)

        self.combo_in_device.clear()
        self.combo_in_device.addItem("Aucune entrée", userData=None)
        for idx, name in in_devices:
            self.combo_in_device.addItem(f"[{idx}] {name}", userData=idx)

        self.combo_midi.clear()
        self.combo_midi.addItem("Aucun", userData=None)
        for name in midi_ports:
            self.combo_midi.addItem(name, userData=name)