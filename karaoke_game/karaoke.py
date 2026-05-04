# sources: https://pyglet.readthedocs.io/en/latest/
import pyglet
from pyglet import window, resource, font
import numpy as np
import sounddevice as sd
import random
import os

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

# import font
font.add_file('./assets/Play-Regular.ttf')
play_reg = font.load('Play')

resource.path = ['./assets']
resource.reindex()
win = pyglet.window.Window(WINDOW_WIDTH, WINDOW_HEIGHT, caption='Captain-Marinaoke')

main_batch = pyglet.graphics.Batch()
bg_batch = pyglet.graphics.Batch()

#load images
bg_img = resource.image('background.png')
player_img = resource.image('rocket.png')
note_img = resource.image('star.png')

planets_img = []
planets_dir = './assets/planets'

# check if folder planets exists
if os.path.exists(planets_dir):
    # go thorugh every file
    for filename in os.listdir(planets_dir):
        # only images png images
        if filename.endswith(('.png')):
            #load image
            img = resource.image(f"planets/{filename}")
            planets_img.append(img)
            
if not planets_img:
    print("Error: No images found in folder 'assets/planets' !")

player_img.anchor_x = player_img.width//2
player_img.anchor_y = player_img.height//2

#background loop
bg_sprites = []
for i in range(2):
    sprite = pyglet.sprite.Sprite(img=bg_img, x=i*WINDOW_WIDTH, y=0, batch=bg_batch)
    # scale background to window
    sprite.scale_x = win.width / bg_img.width
    sprite.scale_y = win.height / bg_img.height
    
    bg_sprites.append(sprite)

# player setup
player = pyglet.sprite.Sprite(img=player_img, x=150, y=WINDOW_HEIGHT//2, batch=main_batch)
player.scale = 0.075

current_score = 0
game_over = False

notes = []
obstacles = []

# game-play setup
spawn_x = win.width

# generation of and notes
for i in range(20):
    note_y = random.randint(100, win.height - 100)
    note = pyglet.sprite.Sprite(img=note_img, x=spawn_x, y=note_y, batch=main_batch)
    note.scale = 0.1
    # ensure note can be only collected once
    note.is_collected = False # type: ignore 
    notes.append(note)

    # generation of obstacles
    obs_y = random.randint(100, win.height - 100)
    # ensures obstacle sare not being spawned upon notes
    while abs(obs_y - note_y) < 100: 
            obs_y = random.randint(100, win.height - 100)

    # selection of random planet image
    random_planet = random.choice(planets_img)
    obs = pyglet.sprite.Sprite(img=random_planet, x=spawn_x + 200, y=obs_y, batch=main_batch)
    obs.scale = 0.8
    obstacles.append(obs)
    # space between note and obstacle
    spawn_x += 400

# set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024 # Number of audio frames per buffer
RATE = 44100 # Audio sampling rate (HZ)
CHANNELS = 1 # Mono audio
current_pitch = 0.0
audio_active = False

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
        print(f'Audio Status: {status}')
    
    data = indata[:, 0]
    current_pitch = get_frequency(data, RATE)

# loading text label
pitch_label = pyglet.text.Label('waiting for audio...', font_name='Play', font_size=20, x=win.width//2, y=win.height//2, anchor_x='center', anchor_y='center')

# open audio input stream
stream = sd.InputStream(
    device=input_device,
    channels=CHANNELS, 
    samplerate=RATE, 
    blocksize=CHUNK_SIZE, 
    callback=audio_callback,
    latency='low' 
)

# convert pitch into y-coordinate
def hz_to_y(frequency, win_height):
    # hold position or go down for no/low pitch
    if frequency <80: 
        return player.y 
    # formula for converting hz to note
    note_value = 12 * np.log2(frequency / 440.0) + 69
    # range for voice
    min_note, max_note = 45, 65
    percentage = (note_value - min_note) / (max_note - min_note)
    return max(0, min(win_height, int(percentage * win_height)))

score_label = pyglet.text.Label(
    text=f'score: {current_score}',
    font_name = 'Play',
    font_size = 15,
    x=790, y=560,
    anchor_x='right',
    color = (255,213,46)
)

game_over_label = pyglet.text.Label(
    text='GAME OVER', 
    font_name='Play', 
    font_size=40,
    x=WINDOW_WIDTH//2, 
    y=WINDOW_HEIGHT//2, 
    anchor_x='center', 
    anchor_y='center', 
    color=(255, 50, 50)
)

def update(dt):
    global current_score, game_over
    
    if game_over:
        return
    # player movement
    target_y = hz_to_y(current_pitch, win.height)
    if current_pitch > 80:
        # movement to target pitch
        player.y += (target_y - player.y) * 0.1 
    else:
        # set gravity effect during silence
        player.y -= 200 * dt
    # keeps player in window
    player.y = max(0, min(win.height, player.y))

    # loops background
    # move first sprite
    bg_sprites[0].x -= 50 * dt
    # reset sprite right
    if bg_sprites[0].x <= -win.width:
        bg_sprites[0].x += win.width
    # stick second background to first
    # -1 for overlapping to seamless looping
    bg_sprites[1].x = bg_sprites[0].x + win.width - 1
        
    # collecting notes
    for note in notes:
        # flying speed
        note.x -= 150 * dt 

        # collision
        if not note.is_collected:
                if (player.x - player.width//2 < note.x + note.width and 
                    player.x + player.width//2 > note.x and
                    player.y - player.height//2 < note.y + note.height and 
                    player.y + player.height//2 > note.y):
                    
                    # collected note
                    note.is_collected = True
                    # hide note
                    note.opacity = 0 
                    current_score += 10
                    score_label.text = f'Score: {current_score}'
    # obstacle managment               
    for obs in obstacles:
            obs.x -= 150 * dt
            
            if (player.x - player.width//2 < obs.x + obs.width and 
                player.x + player.width//2 > obs.x and
                player.y - player.height//2 < obs.y + obs.height and 
                player.y + player.height//2 > obs.y):
                # obstacle touched = end game
                game_over = True

@win.event
def on_draw():
    win.clear()
    bg_batch.draw()
    main_batch.draw()

    if game_over:
        game_over_label.draw()

# game start
with stream:
    pyglet.clock.schedule_interval(update, 1/60.0)
    pyglet.app.run()

