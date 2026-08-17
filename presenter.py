from PyQt5.QtCore import QObject


class SignalGeneratorPresenter(QObject):
    def __init__(self, model, view):
        super().__init__()
        self.model = model
        self.view = view

        out_devs, in_devs = self.model.get_audio_devices()
        midi_ports = self.model.get_midi_ports()
        self.view.populate_devices(out_devs, in_devs, midi_ports)

        self.model.midi_callback_fn = self.on_midi_event_received
        self.view.midiSignal.connect(self.update_ui_from_midi)

        self.view.btn_toggle.clicked.connect(self.on_toggle_play)
        self.view.combo_out_device.currentIndexChanged.connect(self.on_out_device_changed)
        self.view.combo_in_device.currentIndexChanged.connect(self.on_in_device_changed)
        self.view.combo_midi.currentIndexChanged.connect(self.on_midi_port_changed)

        for i in range(self.view.num_oscillators):
            osc_w = self.view.osc_widgets[i]
            mix_w = self.view.mixer_widgets[i]
            model_osc = self.model.oscillators[i]

            osc_w.freq_drawer.set_frequency_bounds(model_osc.freq_min, model_osc.freq_max)

            # Reset
            osc_w.btn_reset_wave.clicked.connect(lambda _, idx=i: self.on_reset_wave(idx))
            osc_w.btn_reset_freq.clicked.connect(lambda _, idx=i: self.on_reset_freq(idx))
            osc_w.btn_reset_vol.clicked.connect(lambda _, idx=i: self.on_reset_vol(idx))
            
            # Entrée Audio
            osc_w.combo_audio_mod.currentIndexChanged.connect(lambda idx_c, idx=i: self.on_audio_mod_source_changed(idx, idx_c))
            osc_w.spin_audio_sens.valueChanged.connect(lambda v, idx=i: self.on_audio_mod_sens_changed(idx, v))

            # Fréquence Fixe
            osc_w.slider_fixed_freq.valueChanged.connect(lambda v, idx=i: self.on_fixed_freq_slider_changed(idx, v))
            osc_w.spin_fixed_freq.valueChanged.connect(lambda v, idx=i: self.on_fixed_freq_spin_changed(idx, v))
            
            # Vitesse Fréquence (0.1s à 60.0s)
            osc_w.slider_speed.valueChanged.connect(lambda v, idx=i: self.on_speed_slider_changed(idx, v))
            osc_w.spin_speed.valueChanged.connect(lambda v, idx=i: self.on_speed_spin_changed(idx, v))

            # Vitesse Volume (0.1s à 60.0s)
            osc_w.slider_vol_speed.valueChanged.connect(lambda v, idx=i: self.on_vol_speed_slider_changed(idx, v))
            osc_w.spin_vol_speed.valueChanged.connect(lambda v, idx=i: self.on_vol_speed_spin_changed(idx, v))
            
            # Fréquences Min / Max
            osc_w.slider_fmin.valueChanged.connect(lambda v, idx=i: self.on_fmin_slider_changed(idx, v))
            osc_w.spin_fmin.valueChanged.connect(lambda v, idx=i: self.on_fmin_spin_changed(idx, v))
            osc_w.slider_fmax.valueChanged.connect(lambda v, idx=i: self.on_fmax_slider_changed(idx, v))
            osc_w.spin_fmax.valueChanged.connect(lambda v, idx=i: self.on_fmax_spin_changed(idx, v))
            
            # Forme d'onde et Activation Modulations
            osc_w.combo_wave.currentIndexChanged.connect(lambda idx_c, idx=i: self.on_waveform_changed(idx, idx_c))
            osc_w.chk_freq_mod.toggled.connect(lambda chk, idx=i: self.on_freq_mod_toggled(idx, chk))
            osc_w.chk_vol_mod.toggled.connect(lambda chk, idx=i: self.on_vol_mod_toggled(idx, chk))

            # Dessin
            osc_w.wave_drawer.waveformChanged.connect(lambda arr, idx=i: self.model.oscillators[idx].set_custom_waveform(arr))
            osc_w.freq_drawer.waveformChanged.connect(lambda arr, idx=i: self.model.oscillators[idx].set_freq_waveform(arr))
            osc_w.vol_drawer.waveformChanged.connect(lambda arr, idx=i: self.model.oscillators[idx].set_vol_waveform(arr))

            # Mixage
            mix_w.chk_enable.toggled.connect(lambda chk, idx=i: self.on_enable_toggled(idx, chk))
            mix_w.combo_channel.currentIndexChanged.connect(lambda idx_c, idx=i: self.on_channel_changed(idx, idx_c))
            mix_w.slider_amp.valueChanged.connect(lambda v, idx=i: self.on_amplitude_changed(idx, v))

    def on_midi_event_received(self, osc_idx, event_type, value):
        self.view.midiSignal.emit(osc_idx, event_type, value)

    def update_ui_from_midi(self, osc_idx, event_type, value):
        osc_w = self.view.osc_widgets[osc_idx]
        mix_w = self.view.mixer_widgets[osc_idx]

        if event_type == 'note_on':
            osc_w.slider_fixed_freq.blockSignals(True)
            osc_w.spin_fixed_freq.blockSignals(True)
            osc_w.slider_fixed_freq.setValue(int(value))
            osc_w.spin_fixed_freq.setValue(value)
            osc_w.slider_fixed_freq.blockSignals(False)
            osc_w.spin_fixed_freq.blockSignals(False)
        elif event_type == 'volume':
            mix_w.slider_amp.blockSignals(True)
            mix_w.slider_amp.setValue(int(value * 100))
            mix_w.lbl_vol.setText(f"{int(value * 100)}%")
            mix_w.slider_amp.blockSignals(False)
        elif event_type == 'speed':
            # Échelle MIDI réétalonnée jusqu'à 60 secondes
            duration = 0.1 + (value / 127.0) * 59.9
            osc_w.slider_speed.blockSignals(True)
            osc_w.spin_speed.blockSignals(True)
            osc_w.slider_speed.setValue(int(duration * 10))
            osc_w.spin_speed.setValue(duration)
            osc_w.slider_speed.blockSignals(False)
            osc_w.spin_speed.blockSignals(False)

    def on_audio_mod_source_changed(self, osc_idx, combo_index):
        mapping = {0: 'none', 1: 'freq', 2: 'volume', 3: 'both'}
        self.model.oscillators[osc_idx].audio_mod_source = mapping.get(combo_index, 'none')

    def on_audio_mod_sens_changed(self, osc_idx, value):
        self.model.oscillators[osc_idx].audio_mod_sensitivity = float(value)

    def on_enable_toggled(self, osc_idx, checked):
        self.model.oscillators[osc_idx].enabled = checked

    def on_toggle_play(self):
        if self.model.is_playing:
            self.model.stop()
            self.view.btn_toggle.setText("Démarrer")
        else:
            self.model.start()
            self.view.btn_toggle.setText("Arrêter")

    def on_reset_wave(self, osc_idx):
        self.view.osc_widgets[osc_idx].wave_drawer.reset_waveform()
        self.model.oscillators[osc_idx].reset_custom_waveform()

    def on_reset_freq(self, osc_idx):
        self.view.osc_widgets[osc_idx].freq_drawer.reset_waveform()
        self.model.oscillators[osc_idx].reset_freq_waveform()

    def on_reset_vol(self, osc_idx):
        self.view.osc_widgets[osc_idx].vol_drawer.reset_waveform()
        self.model.oscillators[osc_idx].reset_vol_waveform()

    def on_fixed_freq_slider_changed(self, osc_idx, value):
        osc_w = self.view.osc_widgets[osc_idx]
        osc_w.spin_fixed_freq.blockSignals(True)
        osc_w.spin_fixed_freq.setValue(float(value))
        osc_w.spin_fixed_freq.blockSignals(False)
        self.model.oscillators[osc_idx].frequency = float(value)

    def on_fixed_freq_spin_changed(self, osc_idx, value):
        osc_w = self.view.osc_widgets[osc_idx]
        osc_w.slider_fixed_freq.blockSignals(True)
        osc_w.slider_fixed_freq.setValue(int(value))
        osc_w.slider_fixed_freq.blockSignals(False)
        self.model.oscillators[osc_idx].frequency = float(value)

    def on_speed_slider_changed(self, osc_idx, raw_value):
        duration = raw_value / 10.0
        osc_w = self.view.osc_widgets[osc_idx]
        osc_w.spin_speed.blockSignals(True)
        osc_w.spin_speed.setValue(duration)
        osc_w.spin_speed.blockSignals(False)
        self.model.oscillators[osc_idx].sweep_duration = duration

    def on_speed_spin_changed(self, osc_idx, duration):
        osc_w = self.view.osc_widgets[osc_idx]
        osc_w.slider_speed.blockSignals(True)
        osc_w.slider_speed.setValue(int(duration * 10))
        osc_w.slider_speed.blockSignals(False)
        self.model.oscillators[osc_idx].sweep_duration = duration

    def on_vol_speed_slider_changed(self, osc_idx, raw_value):
        duration = raw_value / 10.0
        osc_w = self.view.osc_widgets[osc_idx]
        osc_w.spin_vol_speed.blockSignals(True)
        osc_w.spin_vol_speed.setValue(duration)
        osc_w.spin_vol_speed.blockSignals(False)
        self.model.oscillators[osc_idx].vol_sweep_duration = duration

    def on_vol_speed_spin_changed(self, osc_idx, duration):
        osc_w = self.view.osc_widgets[osc_idx]
        osc_w.slider_vol_speed.blockSignals(True)
        osc_w.slider_vol_speed.setValue(int(duration * 10))
        osc_w.slider_vol_speed.blockSignals(False)
        self.model.oscillators[osc_idx].vol_sweep_duration = duration

    def on_fmin_slider_changed(self, osc_idx, value):
        self._apply_fmin_change(osc_idx, float(value))

    def on_fmin_spin_changed(self, osc_idx, value):
        self._apply_fmin_change(osc_idx, float(value))

    def _apply_fmin_change(self, osc_idx, value):
        osc = self.model.oscillators[osc_idx]
        osc_w = self.view.osc_widgets[osc_idx]

        if value > (osc.freq_max - 0.5):
            value = osc.freq_max - 0.5

        osc_w.slider_fmin.blockSignals(True)
        osc_w.spin_fmin.blockSignals(True)
        osc_w.slider_fmin.setValue(int(value))
        osc_w.spin_fmin.setValue(value)
        osc_w.slider_fmin.blockSignals(False)
        osc_w.spin_fmin.blockSignals(False)

        osc.freq_min = float(value)
        osc_w.freq_drawer.set_frequency_bounds(osc.freq_min, osc.freq_max)

    def on_fmax_slider_changed(self, osc_idx, value):
        self._apply_fmax_change(osc_idx, float(value))

    def on_fmax_spin_changed(self, osc_idx, value):
        self._apply_fmax_change(osc_idx, float(value))

    def _apply_fmax_change(self, osc_idx, value):
        osc = self.model.oscillators[osc_idx]
        osc_w = self.view.osc_widgets[osc_idx]

        if value < (osc.freq_min + 0.5):
            value = osc.freq_min + 0.5

        osc_w.slider_fmax.blockSignals(True)
        osc_w.spin_fmax.blockSignals(True)
        osc_w.slider_fmax.setValue(int(value))
        osc_w.spin_fmax.setValue(value)
        osc_w.slider_fmax.blockSignals(False)
        osc_w.spin_fmax.blockSignals(False)

        osc.freq_max = float(value)
        osc_w.freq_drawer.set_frequency_bounds(osc.freq_min, osc.freq_max)

    def on_freq_mod_toggled(self, osc_idx, checked):
        self.model.oscillators[osc_idx].use_freq_modulation = checked

    def on_vol_mod_toggled(self, osc_idx, checked):
        self.model.oscillators[osc_idx].use_vol_modulation = checked

    def on_amplitude_changed(self, osc_idx, value):
        self.model.oscillators[osc_idx].amplitude = value / 100.0
        self.view.mixer_widgets[osc_idx].lbl_vol.setText(f"{value}%")

    def on_waveform_changed(self, osc_idx, combo_index):
        mapping = {
            0: 'sinus',
            1: 'carre',
            2: 'triangle',
            3: 'sawtooth',
            4: 'tangente',
            5: 'white_noise',
            6: 'custom'
        }
        self.model.oscillators[osc_idx].waveform = mapping.get(combo_index, 'sinus')

    def on_channel_changed(self, osc_idx, combo_index):
        mapping = {0: 'left', 1: 'right', 2: 'both'}
        self.model.oscillators[osc_idx].channel = mapping.get(combo_index, 'both')

    def on_out_device_changed(self, index):
        dev_id = self.view.combo_out_device.currentData()
        if dev_id is not None:
            self.model.set_output_device(dev_id)

    def on_in_device_changed(self, index):
        dev_id = self.view.combo_in_device.currentData()
        self.model.set_input_device(dev_id)

    def on_midi_port_changed(self, index):
        port_name = self.view.combo_midi.currentData()
        self.model.set_midi_port(port_name)