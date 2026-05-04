import sounddevice as sd
import numpy as np
from pynput.keyboard import Key, Controller
import collections
import time

# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024 # Number of audio frames per buffer
RATE = 44100 # Audio sampling rate (HZ)
CHANNELS = 1 # Mono audioAT

keyboard = Controller()

MIN_FREQ = 1000
MAX_FREQ = 3000
VOLUME_THRESHOLD = 0.02
MAG_THRESHOLD = 3.0
PURITY_THRESHOLD = 4.0
HISTORY_LEN = 8
CHIRP_DELTA = 300
COOLDOWN = 0.5

freq_history = collections.deque(maxlen=HISTORY_LEN)

last_action_time = 0

# audio input selection
print('Select Input-Device:\n')
devices = sd.query_devices()

# listing of available input devices
input_devices = []
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        print(f'{i}: {dev['name']}')
        input_devices.append(i)

# user selection
input_device = int(input('\n Choose your Input Device (Select number): '))

# audio callback to safe data
def audio_callback(indata, frames, current_time, status):
    global last_action_time
    if status:
        print(status)

    data = indata[:, 0]  # mono
    # get frequency
    rms = np.sqrt(np.mean(data**2))

    # whistle too quiet
    if rms < VOLUME_THRESHOLD:
        freq_history.clear()
        return
    # Fourier-Transformation
    windowed = data * np.hanning(len(data))

    fft_result = np.fft.rfft(windowed)

    magnitudes = np.abs(fft_result)

    freqs = np.fft.rfftfreq(len(windowed), 1/RATE)
    
    # filter whistle notes
    valid_idx = np.where((freqs >= MIN_FREQ) & (freqs <= MAX_FREQ))[0]

    # check for whistle
    if len(valid_idx) == 0:
        return
    # choose strongest whistle
    peak_idx = valid_idx[np.argmax(magnitudes[valid_idx])]

    peak_freq = freqs[peak_idx]

    peak_mag = magnitudes[peak_idx]
    
    mean_mag = np.mean(magnitudes[valid_idx])
    # cancel out other noises than whistle
    purity = peak_mag / mean_mag
    # check if whistle is quiter
    if peak_mag < MAG_THRESHOLD or purity < PURITY_THRESHOLD:
        freq_history.clear()
        return
        
    freq_history.append(peak_freq)
    # check frequency changes
    if len(freq_history) == HISTORY_LEN:
        current_time = time.time()
        if (current_time - last_action_time) > COOLDOWN:
            start_freq = freq_history[0]
            end_freq = freq_history[-1]
            delta = end_freq - start_freq
            # direction based on frequency
            # going up
            if delta > CHIRP_DELTA:
                print(f"Hoch ({start_freq:.0f}Hz -> {end_freq:.0f}Hz)")
                keyboard.press(Key.up)
                keyboard.release(Key.up)
                last_action_time = current_time
                freq_history.clear()
            # going down
            if delta < -CHIRP_DELTA:
                print(f"Runter ({start_freq:.0f}Hz -> {end_freq:.0f}Hz)")
                keyboard.press(Key.down)
                keyboard.release(Key.down)
                last_action_time = current_time
                freq_history.clear()

# open audio input stream
stream = sd.InputStream(
    device=input_device,
    channels=CHANNELS, 
    samplerate=RATE, 
    blocksize=CHUNK_SIZE, 
    callback=audio_callback,
    latency='low' 
)

with stream:
    print("\nLets whistleeeee")
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nNightynight")