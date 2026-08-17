import sounddevice as sd
import numpy as np
import mido

class Oscillator:
    def __init__(self, sample_rate=44100, custom_wave_points=512):
        self.sample_rate = sample_rate
        self.enabled = False
        self.frequency = 440.0
        self.amplitude = 0.1
        self.waveform = 'sinus'
        self.channel = 'both'
        
        # 1. Modulation Fréquence
        self.use_freq_modulation = False
        self.freq_min = 100.0
        self.freq_max = 1000.0
        self.sweep_duration = 2.0
        self._freq_phase = 0.0
        
        # 2. Modulation Volume
        self.use_vol_modulation = False
        self.vol_sweep_duration = 2.0
        self._vol_phase = 0.0

        # 3. Asservissement par Entrée Audio
        self.audio_mod_source = 'none'  # 'none', 'freq', 'volume', 'both'
        self.audio_mod_sensitivity = 1.0

        self.custom_wave_points = custom_wave_points
        self.custom_waveform = np.zeros(self.custom_wave_points, dtype=np.float32)
        self.freq_waveform = np.full(self.custom_wave_points, 0.5, dtype=np.float32)
        self.vol_waveform = np.full(self.custom_wave_points, 1.0, dtype=np.float32)
        
        self._phase = 0.0

    def set_custom_waveform(self, array_values):
        self.custom_waveform = array_values.astype(np.float32)

    def set_freq_waveform(self, array_values):
        self.freq_waveform = array_values.astype(np.float32)

    def set_vol_waveform(self, array_values):
        self.vol_waveform = array_values.astype(np.float32)

    def reset_custom_waveform(self):
        self.custom_waveform = np.zeros(self.custom_wave_points, dtype=np.float32)

    def reset_freq_waveform(self):
        self.freq_waveform = np.full(self.custom_wave_points, 0.5, dtype=np.float32)

    def reset_vol_waveform(self):
        self.vol_waveform = np.full(self.custom_wave_points, 1.0, dtype=np.float32)

    def generate_chunk(self, frames, audio_in_level=0.0):
        if not self.enabled:
            return np.zeros((frames, 2), dtype=np.float32)

        input_norm = float(np.clip(audio_in_level * self.audio_mod_sensitivity, 0.0, 1.0))

        # A) CALCUL FRÉQUENCE
        if self.audio_mod_source in ['freq', 'both']:
            target_freq = self.freq_min + input_norm * (self.freq_max - self.freq_min)
        elif self.use_freq_modulation:
            self._freq_phase = (self._freq_phase + (frames / (self.sweep_duration * self.sample_rate))) % 1.0
            idx = int(self._freq_phase * (self.custom_wave_points - 1))
            norm_freq = self.freq_waveform[idx]
            target_freq = self.freq_min + norm_freq * (self.freq_max - self.freq_min)
        else:
            target_freq = self.frequency

        # B) CALCUL VOLUME
        if self.audio_mod_source in ['volume', 'both']:
            target_amp = self.amplitude * input_norm
        elif self.use_vol_modulation:
            self._vol_phase = (self._vol_phase + (frames / (self.vol_sweep_duration * self.sample_rate))) % 1.0
            idx = int(self._vol_phase * (self.custom_wave_points - 1))
            norm_vol = self.vol_waveform[idx]
            target_amp = self.amplitude * norm_vol
        else:
            target_amp = self.amplitude

        # C) CALCUL D'ONDE CONTINU
        phase_step = max(20.0, float(target_freq)) / self.sample_rate
        phases = (self._phase + np.arange(frames, dtype=np.float32) * phase_step) % 1.0
        self._phase = (self._phase + frames * phase_step) % 1.0

        # D) GENERATION FORMES D'ONDE
        if self.waveform == 'sinus':
            data = np.sin(2.0 * np.pi * phases, dtype=np.float32)
        elif self.waveform == 'carre':
            data = np.where(phases < 0.5, 1.0, -1.0).astype(np.float32)
        elif self.waveform == 'triangle':
            data = (2.0 * np.abs(2.0 * (phases - np.floor(phases + 0.5))) - 1.0).astype(np.float32)
        elif self.waveform == 'sawtooth':
            data = (2.0 * (phases - np.floor(phases + 0.5))).astype(np.float32)
        elif self.waveform == 'tangente':
            raw_tan = np.tan(np.pi * (phases - 0.5))
            data = np.clip(raw_tan / 3.0, -1.0, 1.0).astype(np.float32)
        elif self.waveform == 'white_noise':
            data = np.random.uniform(-1.0, 1.0, frames).astype(np.float32)
        elif self.waveform == 'custom':
            x_custom = np.linspace(0.0, 1.0, len(self.custom_waveform), endpoint=False)
            data = np.interp(phases, x_custom, self.custom_waveform).astype(np.float32)
        else:
            data = np.zeros(frames, dtype=np.float32)

        data *= float(target_amp)

        # E) STÉRÉO
        stereo_data = np.zeros((frames, 2), dtype=np.float32)
        if self.channel == 'left':
            stereo_data[:, 0] = data
        elif self.channel == 'right':
            stereo_data[:, 1] = data
        else:
            stereo_data[:, 0] = data
            stereo_data[:, 1] = data

        return stereo_data


class SignalGeneratorModel:
    def __init__(self, sample_rate=44100, num_oscillators=10):
        self.sample_rate = sample_rate
        self.num_oscillators = num_oscillators
        self.oscillators = [Oscillator(sample_rate=self.sample_rate) for _ in range(num_oscillators)]
        
        self.output_device_index = None
        self.input_device_index = None
        self.is_playing = False
        
        self._out_stream = None
        self._in_stream = None
        self.current_input_level = 0.0

        self.midi_in = None
        self.midi_port_name = None
        self.midi_callback_fn = None

    @staticmethod
    def get_audio_devices():
        devices = sd.query_devices()
        output_devices = []
        input_devices = []
        for idx, dev in enumerate(devices):
            if dev['max_output_channels'] > 0:
                output_devices.append((idx, dev['name']))
            if dev['max_input_channels'] > 0:
                input_devices.append((idx, dev['name']))
        return output_devices, input_devices

    @staticmethod
    def get_midi_ports():
        try:
            import mido
            return mido.get_input_names()
        except Exception:
        # En cas d'absence du backend dans l'exe, on retourne une liste vide
            return []

    def set_midi_port(self, port_name):
        if self.midi_in:
            self.midi_in.close()
            self.midi_in = None

        self.midi_port_name = port_name
        if port_name:
            try:
                self.midi_in = mido.open_input(port_name, callback=self._on_midi_message)
            except Exception as e:
                print(f"Erreur MIDI : {e}")

    def _on_midi_message(self, msg):
        if msg.type == 'note_on' and msg.velocity > 0:
            freq = 440.0 * (2.0 ** ((msg.note - 69) / 12.0))
            osc_idx = min(msg.channel, self.num_oscillators - 1)
            self.oscillators[osc_idx].frequency = freq
            if self.midi_callback_fn:
                self.midi_callback_fn(osc_idx, 'note_on', freq)

        elif msg.type == 'control_change':
            osc_idx = min(msg.channel, self.num_oscillators - 1)
            if msg.control == 7:
                amp = msg.value / 127.0
                self.oscillators[osc_idx].amplitude = amp
                if self.midi_callback_fn:
                    self.midi_callback_fn(osc_idx, 'volume', amp)

    def _audio_in_callback(self, indata, frames, time_info, status):
        if len(indata) > 0:
            peak = np.max(np.abs(indata))
            self.current_input_level = float(peak)

    def _audio_out_callback(self, outdata, frames, time_info, status):
        mix = np.zeros((frames, 2), dtype=np.float32)
        in_lvl = self.current_input_level

        for osc in self.oscillators:
            if osc.enabled:
                mix += osc.generate_chunk(frames, audio_in_level=in_lvl)
        
        np.clip(mix, -1.0, 1.0, out=outdata)

    def start(self):
        if not self.is_playing:
            self._out_stream = sd.OutputStream(
                device=self.output_device_index,
                samplerate=self.sample_rate,
                channels=2,
                blocksize=512,
                callback=self._audio_out_callback
            )
            self._out_stream.start()

            if self.input_device_index is not None:
                try:
                    self._in_stream = sd.InputStream(
                        device=self.input_device_index,
                        samplerate=self.sample_rate,
                        channels=1,
                        blocksize=512,
                        callback=self._audio_in_callback
                    )
                    self._in_stream.start()
                except Exception as e:
                    print(f"Erreur d'entrée audio : {e}")

            self.is_playing = True

    def stop(self):
        if self.is_playing:
            if self._out_stream:
                self._out_stream.stop()
                self._out_stream.close()
                self._out_stream = None
            if self._in_stream:
                self._in_stream.stop()
                self._in_stream.close()
                self._in_stream = None
            self.is_playing = False

        if self.midi_in:
            self.midi_in.close()

    def set_output_device(self, device_index):
        restart = self.is_playing
        if restart: self.stop()
        self.output_device_index = device_index
        if restart: self.start()

    def set_input_device(self, device_index):
        restart = self.is_playing
        if restart: self.stop()
        self.input_device_index = device_index
        if restart: self.start()