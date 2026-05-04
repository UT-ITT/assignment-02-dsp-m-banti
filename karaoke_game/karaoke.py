# sources: https://pyglet.readthedocs.io/en/latest/
import pyglet
from pyglet import window, resource, font, shapes
from pyglet.window import key
import numpy as np
import sounddevice as sd
from mido import MidiFile

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

# graphics batches for rendering
main_batch = pyglet.graphics.Batch()
bg_batch = pyglet.graphics.Batch()

resource.path = ['./assets']
resource.reindex()
win = pyglet.window.Window(WINDOW_WIDTH, WINDOW_HEIGHT, caption='Captain-Marinaoke')

# import font
font.add_file('./assets/Play-Regular.ttf')
play_reg = font.load('Play')

#load images
bg_img = resource.image('popcorn_bg.png')
bg_sprite = pyglet.sprite.Sprite(img=bg_img, batch=bg_batch)
player_img = resource.image('popcorn.png')

# player setup
player_img.anchor_x = player_img.width // 2
player_img.anchor_y = player_img.height // 2
player = pyglet.sprite.Sprite(img=player_img, x=150, y=WINDOW_HEIGHT//2, batch=main_batch)
player.scale = 0.1

# load and queue background music
try:
    music = pyglet.resource.media('freude.mp3', streaming=True) 
    player_music = pyglet.media.Player()
    player_music.queue(music)
except Exception as e:
    print(f"No popcorni: {e}")
    player_music = None 

# set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024 # Number of audio frames per buffer
RATE = 44100 # Audio sampling rate (HZ)
CHANNELS = 1 # Mono audio

VOLUME_THRESHOLD = 0.02
PURITY_THRESHOLD = 3.0

current_pitch = 0.0
score = 0
game_state = "START"
countdown_value = 3
# labels
start_batch = pyglet.graphics.Batch()
start_label = pyglet.text.Label('Press SPACE to Start', font_name='Play', font_size=40,
                                x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2,
                                anchor_x='center', anchor_y='center',
                                batch=start_batch)

countdown_batch = pyglet.graphics.Batch()
countdown_label = pyglet.text.Label('3', font_name='Play', font_size=80,
                                    x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2,
                                    anchor_x='center', anchor_y='center',
                                    color=(255, 255, 50, 255),
                                    batch=countdown_batch)

gameover_batch = pyglet.graphics.Batch()

gameover_label = pyglet.text.Label('GAME OVER', font_name='Play', font_size=54,
                                   x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2 + 40,
                                   anchor_x='center', anchor_y='center',
                                   color=(255, 50, 50, 255),
                                   batch=gameover_batch)

f_score_label = pyglet.text.Label('Final Score: 0', font_name='Play', font_size=36,
                                      x=WINDOW_WIDTH//2, y=WINDOW_HEIGHT//2 - 30,
                                      anchor_x='center', anchor_y='center',
                                      batch=gameover_batch)

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

# frequency logic
def get_frequency(data, rate):
    # caclulate frequence with FFT
    rms = np.sqrt(np.mean(data**2))
    if rms < VOLUME_THRESHOLD:
        return 0.0

    window = np.hanning(len(data))
    data = data * window
    
    fft_data = np.fft.rfft(data)
    freqs = np.fft.rfftfreq(len(data), 1.0 / rate)
    
    magnitudes = np.abs(fft_data)
    peak_idx = np.argmax(magnitudes)

    peak_mag = magnitudes[peak_idx]
    mean_mag = np.mean(magnitudes)

    if mean_mag == 0:
        return 0.0
    
    purity = peak_mag / mean_mag

    # cancel out noise, so if the input is lower then 0.5, 
    # then it will be recognized as silence
    if peak_mag > 0.5 and purity > PURITY_THRESHOLD:
        return freqs[peak_idx]
    return 0.0
    
print("Moin MIDI")
song_notes_hz = []

AUDIO_OFFSET = 0.5

# read midi file
try:
    mid = MidiFile('./assets/freude.mid')
    current_time = 0.0
    for msg in mid:
        current_time += msg.time
        if not msg.is_meta and msg.type == 'note_on' and msg.velocity > 0 and msg.channel == 0:
            freq = 440.0 * (2.0 ** ((msg.note - 69) / 12.0))
            song_notes_hz.append({
                'freq': freq,
                'time': current_time + AUDIO_OFFSET
            })
    print("Notes sind da")
except Exception as e:
    print("Fehlermeler no MIDI :((()))")

def audio_callback(indata, frames, time, status):
    global current_pitch
    if status:
        print(f'Audio Status: {status}')
    
    data = indata[:, 0]

    current_pitch = get_frequency(data, RATE)

# convert pitch into y-coordinate
def pitch_to_y(pitch):
    # hold position for low pitch
    if pitch < 50:
        return 50
    # map frequency range to screen height
    y = ((pitch - 80) / 720.0) * 400 + 100
    return max(50, min(550, y))

# labels
score_label = pyglet.text.Label('Score: 0', font_name='Play', font_size=24,
                                x=20, y=WINDOW_HEIGHT-40, batch=main_batch)
instruction_label = pyglet.text.Label('Lets hear you sing the song: ODE TO JOY', font_name='Play', font_size=24,
                                x=20, y=WINDOW_HEIGHT-70, batch=main_batch)

target_shapes = []
PLAYER_X = 150
SPEED = 150.0

start_x = 800

# generate target blocks based on midi data
for note_data in song_notes_hz:
    freq = note_data['freq']
    note_time = note_data['time']
    target_y = pitch_to_y(freq)
    # calculate start x based on timing and speed
    start_x = PLAYER_X + (note_time * SPEED)
    block = shapes.Rectangle(x=start_x, y=target_y - 15, width=60, height=30, color=(200, 50, 50), batch=bg_batch)
    target_shapes.append({'shape': block, 'freq': freq, 'hit': False})


@win.event
def on_key_press(symbol, modifiers):
    global game_state
    # start game
    if game_state == "START" and symbol == key.SPACE:
        game_state = "COUNTDOWN"
        pyglet.clock.schedule_interval(update_countdown, 1.0)

def update_countdown(dt):
    global countdown_value, game_state
    
    countdown_value -= 1
    # countdown to start game
    if countdown_value > 0:
        countdown_label.text = str(countdown_value)
    elif countdown_value == 0:
        countdown_label.text = "GO"
    else:

        pyglet.clock.unschedule(update_countdown) 

        game_state = "PLAYING"

        if player_music:
            player_music.play()

def update(dt):
    global score, current_pitch, game_state
    
    if game_state != "PLAYING":
        return
    # player movement to target pitch
    target_y = pitch_to_y(current_pitch)
    player.y += (target_y - player.y) * 10 * dt
    # manage target blocks
    for target in target_shapes:
        target['shape'].x -= 150 * dt 
        # player collision area
        if 110 < target['shape'].x < 170:
            # highlight block in hit zone
            target['shape'].color = (255, 255, 50) 
        # check if sung pitch matches target frequency
            if current_pitch > 0 and abs(current_pitch - target['freq']) < 30:
                if not target['hit']:
                    target['hit'] = True
                    score += 10
                    score_label.text = f'Score: {score}'
        # block passed player
        elif target['shape'].x <= 110:
            # green success
            if target['hit']:
                target['shape'].color = (50, 255, 50) 
            # grey missed
            else:
                target['shape'].color = (100, 100, 100) 

    # check game over condition (all blocks passed)
    if len(target_shapes) > 0:
        final_block = target_shapes[-1]
        if final_block['shape'].x < -100:
            game_state = "GAMEOVER"
            f_score_label.text = f'Final Score: {score}'

@win.event
def on_draw():
    win.clear()
    
    if game_state == "START":
        start_batch.draw()
        
    elif game_state == "COUNTDOWN":
        countdown_batch.draw()
        
    elif game_state == "PLAYING":
        bg_batch.draw()
        main_batch.draw()

    elif game_state == "GAMEOVER":
        gameover_batch.draw()

stream = sd.InputStream(
    device=input_device,
    channels=CHANNELS,
    samplerate=RATE,
    blocksize=CHUNK_SIZE,
    callback=audio_callback,
    latency='low'
)

if __name__ == '__main__':
    with stream:
        print("\nSing for meeee")
        
        pyglet.clock.schedule_interval(update, 1/60.0)
        pyglet.app.run()