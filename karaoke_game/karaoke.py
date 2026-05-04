# sources: https://pyglet.readthedocs.io/en/latest/
import pyglet
from pyglet import window, resource, font
import numpy as np
import sounddevice as sd

# import font
font.add_file('./assets/Play-Regular.tff')
play_reg = font.load('Play Reg')

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

# set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024 # Number of audio frames per buffer
RATE = 44100 # Audio sampling rate (HZ)
CHANNELS = 1 # Mono audio

# audio input selection
print("Select Input-Device:\n")
devices = sd.query_devices()

# listing of available input devices
input_devices = []
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        print(f"{i}: {dev['name']}")
        input_devices.append(i)

# user selection
input_device = int(input("\n Choose your Input Device (Select number): "))

# frequency logic
def get_frequency(data, rate):
    # caclulate frequence with FFT
    window = np.hanning(len(data))
    data = data * window
    
    fft_data = np.fft.rfft(data)
    freqs = np.fft.rfftfreq(len(data), 1.0 / rate)
    
    magnitudes = np.abs(fft_data)
    peak_index = np.argmax(magnitudes)
    
    # cancel out noise, so if the input is lower then 0.5, 
    # then it will be recognized as silence
    if magnitudes[peak_index] > 0.5: 
        return freqs[peak_index]
    return 0.0

def audio_callback(indata, frames, time, status):
    global current_pitch
    if status:
        print(f"Audio Status: {status}")
    
    data = indata[:, 0]
    current_pitch = get_frequency(data, RATE)

current_pitch = 0.0
audio_active = False

resource.path = ['./assets']
resource.reindex()
win = pyglet.window.Window(WINDOW_WIDTH, WINDOW_HEIGHT, caption="Marinaoke")

# loading text label
pitch_label = pyglet.text.Label('waiting for audio...', font_name='Play Reg', font_size=20, x=win.width//2, y=win.height//2, anchor_x='center', anchor_y='center')


# functions as collection to draw a batch
main_batch = pyglet.graphics.Batch()

current_score = 0

score_label = pyglet.text.Label(
    text=f"score: {current_score}",
    font_name = 'Play Reg',
    font_size = 15,
    x=790, y=560,
    anchor_x='right',
    color = (255,213,46)
)
# open audio input stream
stream = sd.InputStream(
    device=input_device,
    channels=CHANNELS, 
    samplerate=RATE, 
    blocksize=CHUNK_SIZE, 
    callback=audio_callback,
    latency='low' 
)

def update(dt):
    pass


@win.event
def on_draw():
    win.clear()
    pitch_label.draw()
    score_label.draw()

with stream:
    pyglet.clock.schedule_interval(update, 1/60.0)

pyglet.app.run()



# get background asset
# bg_image = resource.image("background.png")

# create background batch
#bg_batch = pyglet.graphics.Batch()

#bg_sprites = []