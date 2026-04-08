from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import math

# --- Инициализация ---
app = Ursina()
window.title = "Horro mini game(Magadan)"
window.borderless = False
window.fullscreen = False
window.exit_button.visible = False
window.fps_counter.enabled = False

# --- Глобальные переменные и настройки ---
game_state = 'menu' # menu, game, shop, gameover
money = 0
high_score = 0
current_skin = 'default'
current_song = 'default'

# Настройки мира
MAP_SIZE = 30
CELL_SIZE = 4
WALL_HEIGHT = 5
GRAVITY = 0.8
JUMP_FORCE = 7

# --- Генерация ресурсов (Текстуры и Звуки) ---

# 1. Текстура фона (Используем встроенную 'brick' для главного меню)
scary_bg_tex = 'brick'

# 2. Текстуры кирпича и пола
brick_tex = 'brick'
floor_tex = 'white_cube'

# 3. Синтез звуков
class SoundGen:
    @staticmethod
    def play_step():
        pass

    @staticmethod
    def play_pickup():
        print('Sound: Pickup')

    @staticmethod
    def play_jump():
        print('Sound: Jump')

    @staticmethod
    def play_monster():
        print('Sound: Monster Growl')

    @staticmethod
    def play_music():
        print('Music: Playing...')

# --- Классы Сущностей ---

# Ключ для квеста
class KeyItem(Entity):
    def __init__(self, position):
        super().__init__(
            model='cube',
            color=color.gold,
            scale=(0.5, 0.5, 0.5),
            position=position,
            collider='box'
        )
        self.rotation_speed = 100

    def update(self):
        self.rotation_y += self.rotation_speed * time.dt
        self.y += math.sin(time.time() * 3) * 0.005

# Монстр
class Monster(Entity):
    def __init__(self, position):
        super().__init__(position=position)
        self.speed = 4
        self.state = 'idle'
        
        self.body = Entity(parent=self, model='cube', color=color.black, scale=(0.8, 1.2, 0.5), position=(0, 1.2, 0), collider='box')
        self.head = Entity(parent=self, model='cube', color=color.dark_gray, scale=(0.5, 0.5, 0.5), position=(0, 2.1, 0))
        self.eye_l = Entity(parent=self.head, model='cube', color=color.red, scale=(0.2, 0.1, 0.1), position=(-0.15, 0.1, 0.25))
        self.eye_r = Entity(parent=self.head, model='cube', color=color.red, scale=(0.2, 0.1, 0.1), position=(0.15, 0.1, 0.25))
        
        self.arm_l = Entity(parent=self, model='cube', color=color.black, scale=(0.25, 1.2, 0.25), position=(-0.6, 1.4, 0), origin_y=-0.5)
        self.arm_r = Entity(parent=self, model='cube', color=color.black, scale=(0.25, 1.2, 0.25), position=(0.6, 1.4, 0), origin_y=-0.5)
        self.leg_l = Entity(parent=self, model='cube', color=color.black, scale=(0.3, 1.2, 0.3), position=(-0.25, 0.6, 0), origin_y=-0.5)
        self.leg_r = Entity(parent=self, model='cube', color=color.black, scale=(0.3, 1.2, 0.3), position=(0.25, 0.6, 0), origin_y=-0.5)

    def update(self):
        if game_state != 'game': return

        self.speed = 4 + (time.time() - game_start_time) * 0.05
        dist = distance_xz(self.position, player.position)
        
        walk_cycle = time.time() * (self.speed * 2)
        if dist < 20:
            self.arm_l.rotation_x = math.sin(walk_cycle) * 40
            self.arm_r.rotation_x = -math.sin(walk_cycle) * 40
            self.leg_l.rotation_x = -math.sin(walk_cycle) * 40
            self.leg_r.rotation_x = math.sin(walk_cycle) * 40
            self.body.y = 1.2 + abs(math.sin(walk_cycle * 2)) * 0.05

        self.look_at_2d(player.position, 'y')
        hit_info = raycast(self.position + Vec3(0, 1, 0), self.forward, distance=1.5, ignore=(self, self.body, self.head, self.arm_l, self.arm_r, self.leg_l, self.leg_r))
        
        if not hit_info.hit:
            self.position += self.forward * self.speed * time.dt
        else:
            self.rotation_y += 90 * time.dt
            if random.random() < 0.01: 
                self.position += self.forward * 2

        if dist < 1.5:
            die()

# Улучшенный контроллер игрока с анимацией "переваливания"
class PlayerController(FirstPersonController):
    def __init__(self):
        super().__init__()
        self.speed = 6
        self.jump_height = JUMP_FORCE
        self.gravity = GRAVITY
        self.step_timer = 0
        self.grounded = False
        
        # Переменные для анимации покачивания (Sway)
        self.sway_speed = 10
        self.sway_amount = 1.5

    def update(self):
        if game_state != 'game': return
        
        # Границы карты
        limit = (MAP_SIZE * CELL_SIZE) / 2 - 2
        if self.x > limit: self.x = limit
        if self.x < -limit: self.x = -limit
        if self.z > limit: self.z = limit
        if self.z < -limit: self.z = -limit

        # Проверка на землю
        ray = raycast(self.position + Vec3(0, 0.5, 0), Vec3(0, -1, 0), ignore=(self,), distance=1)
        self.grounded = ray.hit

        # Звук шагов
        if self.grounded and (held_keys['w'] or held_keys['a'] or held_keys['s'] or held_keys['d']):
            self.step_timer += time.dt * (self.speed / 4)
            if self.step_timer > 0.5:
                SoundGen.play_step()
                self.step_timer = 0
            
            # Анимация покачивания камеры (Sway) при ходьбе
            sway = math.sin(time.time() * self.sway_speed) * self.sway_amount
            camera.rotation_z = sway
            
        else:
            # Возвращаем камеру в нормальное положение
            camera.rotation_z = lerp(camera.rotation_z, 0, time.dt * 5)

        # Запрет на запрыгивание на стены
        if not self.grounded:
            wall_check = raycast(self.position, self.forward, distance=0.8, ignore=(self,))
            if wall_check.hit and wall_check.world_point.y > self.y:
                die()

        super().update()

# --- UI и Меню ---

# Главное меню
main_menu = Entity(parent=camera.ui, enabled=True)
# Фон главного меню с текстурой
bg = Entity(parent=main_menu, model='quad', scale=(2, 1), texture=scary_bg_tex, color=color.red)
Text(parent=main_menu, text='Horro mini game(Magadan)', y=0.3, scale=2, origin=(0,0), color=color.black)
play_btn = Button(parent=main_menu, text='PLAY', y=0.1, scale=(0.3, 0.1), color=color.azure)
shop_btn = Button(parent=main_menu, text='SHOP', y=-0.05, scale=(0.3, 0.1), color=color.orange)
quit_btn = Button(parent=main_menu, text='QUIT', y=-0.2, scale=(0.3, 0.1), color=color.gray)

# Магазин
# Магазин
shop_menu = Entity(parent=camera.ui, enabled=False)
# Фон магазина оставляем черным (без панели)
Text(parent=shop_menu, text='SHOP', y=0.4, scale=2, origin=(0,0))

# Глобальный текст денег
money_text = Text(text=f'Money: ${money}', position=(-0.85, 0.4), scale=1.5, color=color.gold)

# Товары
items = [
    {'name': 'Red Killer', 'type': 'skin', 'price': 100, 'color': color.red, 'owned': False},
    {'name': 'Blue Killer', 'type': 'skin', 'price': 150, 'color': color.blue, 'owned': False},
    {'name': 'Dark Music', 'type': 'song', 'price': 50, 'owned': False},
    {'name': 'Fast Music', 'type': 'song', 'price': 50, 'owned': False}
]

shop_buttons = []
for i, item in enumerate(items):
    # Добавили z=-1, чтобы кнопки были поверх
    btn = Button(parent=shop_menu, text=f"{item['name']} - ${item['price']}", y=0.1 - i*0.12, scale=(0.5, 0.08), z=-1)
    btn.item = item
    shop_buttons.append(btn)

# Кнопка BACK с z=-1 и чуть увеличенным размером
# ... (код создания товаров shop_buttons) ...

# Создаем кнопку Back
back_btn = Button(parent=shop_menu, text='BACK', y=-0.4, scale=(0.25, 0.1), color=color.gray, z=-1)

# Назначаем действие напрямую при нажатии
def go_to_menu():
    global game_state
    shop_menu.enabled = False
    main_menu.enabled = True
    game_state = 'menu'
    print("Возврат в меню") # Для проверки

back_btn.on_click = go_to_menu



# HUD (В игре)
hud = Entity(parent=camera.ui, enabled=False)
hud_keys = Text(parent=hud, text='Keys: 0/3', position=(-0.85, 0.45), scale=1.5, color=color.gold)
hud_time = Text(parent=hud, text='Time: 0s', position=(0, 0.45), origin=(0,0), scale=1.5, color=color.white)
hud_msg = Text(parent=hud, text='', position=(0, 0.2), origin=(0,0), scale=2, color=color.red)

# Экран смерти
death_screen = Entity(parent=camera.ui, enabled=False)
death_bg = Entity(parent=death_screen, model='quad', scale=(2, 1), color=color.black)
death_text = Text(parent=death_screen, text='YOU DIED', scale=3, origin=(0,0), color=color.red)
death_score = Text(parent=death_screen, text='', y=-0.1, scale=2, origin=(0,0))
death_menu_btn = Button(parent=death_screen, text='MAIN MENU', y=-0.3, scale=(0.3, 0.1))

# --- Логика Игры ---

# Сцена
ground = Entity(model='plane', texture=floor_tex, scale=(MAP_SIZE*CELL_SIZE, 1, MAP_SIZE*CELL_SIZE), collider='box', texture_scale=(10,10))
Sky(color=color.black)

# Стены и Лабиринт
walls = []
def generate_map():
    for w in walls: destroy(w)
    walls.clear()
    
    for z in range(-MAP_SIZE // 2, MAP_SIZE // 2):
        for x in range(-MAP_SIZE // 2, MAP_SIZE // 2):
            if abs(x) == MAP_SIZE // 2 - 1 or abs(z) == MAP_SIZE // 2 - 1:
                w = Entity(model='cube', texture=brick_tex, color=color.light_gray, position=(x*CELL_SIZE, WALL_HEIGHT/2, z*CELL_SIZE), scale=(CELL_SIZE, WALL_HEIGHT, CELL_SIZE), collider='box')
                walls.append(w)
            elif random.random() < 0.15:
                if abs(x) < 2 and abs(z) < 2: continue
                w = Entity(model='cube', texture=brick_tex, color=color.light_gray, position=(x*CELL_SIZE, WALL_HEIGHT/2, z*CELL_SIZE), scale=(CELL_SIZE, WALL_HEIGHT, CELL_SIZE), collider='box')
                walls.append(w)

generate_map()

player = PlayerController()
mouse.locked = False
monster = Monster(position=(0, 0, 15))
flashlight = SpotLight(parent=camera, y=0, z=0, color=color.white, fov=60, shadows=True)
flashlight.enabled = True

keys_collected = 0
required_keys = 3
key_entities = []

def start_game():
    global game_state, game_start_time, keys_collected
    game_state = 'game'
    game_start_time = time.time()
    keys_collected = 0
    
    player.position = (0, 10, 0)
    player.rotation = (0, 0, 0)
    player.enabled = True
    player.cursor.visible = False
    mouse.locked = True
    
    monster.position = (0, 0, 15)
    monster.speed = 4
    
    for k in key_entities: destroy(k)
    key_entities.clear()
    for _ in range(required_keys):
        while True:
            kx = random.randint(-MAP_SIZE//2 + 2, MAP_SIZE//2 - 2) * CELL_SIZE
            kz = random.randint(-MAP_SIZE//2 + 2, MAP_SIZE//2 - 2) * CELL_SIZE
            if distance((kx, 0, kz), player.position) > 10:
                key_entities.append(KeyItem(position=(kx, 1, kz)))
                break
    
    main_menu.enabled = False
    shop_menu.enabled = False
    death_screen.enabled = False
    hud.enabled = True
    hud_msg.text = ''

def die():
    global game_state, money, high_score
    game_state = 'gameover'
    player.enabled = False
    player.cursor.visible = True
    mouse.locked = False
    flashlight.enabled = False
    
    survived_time = int(time.time() - game_start_time)
    earned = survived_time * 10
    money += earned
    if survived_time > high_score: high_score = survived_time
    
    money_text.text = f'Money: ${money}' # Обновляем деньги
    death_score.text = f'Survived: {survived_time}s\nEarned: ${earned}'
    death_screen.enabled = True
    hud.enabled = False

def update():
    global keys_collected
    
    if game_state == 'game':
        elapsed = int(time.time() - game_start_time)
        hud_time.text = f'Time: {elapsed}s'
        hud_keys.text = f'Keys: {keys_collected}/{required_keys}'
        
        for k in key_entities[:]:
            if distance(player.position, k.position) < 2:
                SoundGen.play_pickup()
                keys_collected += 1
                key_entities.remove(k)
                destroy(k)
                if keys_collected >= required_keys:
                    win_game()

        if held_keys['f']:
            flashlight.enabled = not flashlight.enabled
            invoke(setattr, flashlight, 'enabled', flashlight.enabled, delay=0.2)

def win_game():
    global game_state, money
    game_state = 'gameover'
    player.enabled = False
    player.cursor.visible = True
    hud_msg.text = 'YOU ESCAPED!'
    hud_msg.color = color.green
    money += 500
    money_text.text = f'Money: ${money}' # Обновляем деньги
    invoke(die, delay=3)

def update_shop():
    # Обновляем текст денег
    money_text.text = f'Money: ${money}'
    
    for btn in shop_buttons:
        item = btn.item
        if item['owned']:
            if (item['type'] == 'skin' and current_skin == item['name']) or \
               (item['type'] == 'song' and current_song == item['name']):
                btn.text = f"{item['name']} (Equipped)"
                btn.color = color.green
            else:
                btn.text = f"{item['name']} (Equip)"
                btn.color = color.azure
        else:
            btn.text = f"{item['name']} - ${item['price']}"
            btn.color = color.orange

def input(key):
    global game_state, current_skin, current_song
    
    if key == 'escape':
        if game_state == 'game':
            die()
    
    if game_state == 'menu':
        if play_btn.hovered and key == 'left mouse down':
            start_game()
        if shop_btn.hovered and key == 'left mouse down':
            main_menu.enabled = False
            shop_menu.enabled = True
            update_shop() # Обновляем магазин и деньги при входе
        if quit_btn.hovered and key == 'left mouse down':
            application.quit()
            
    elif game_state == 'shop':
        # Проверка кнопки "BACK"
        if back_btn.hovered and key == 'left mouse down':
            shop_menu.enabled = False
            main_menu.enabled = True
            game_state = 'menu'
        
        # Проверка кнопок товаров
        for btn in shop_buttons:
            if btn.hovered and key == 'left mouse down':
                item = btn.item
                if item['owned']:
                    if item['type'] == 'skin':
                        current_skin = item['name']
                        monster.body.color = item['color']
                    elif item['type'] == 'song':
                        current_song = item['name']
                    update_shop()
                else:
                    if money >= item['price']:
                        money -= item['price']
                        item['owned'] = True
                        update_shop()

    elif game_state == 'gameover':
        if death_menu_btn.hovered and key == 'left mouse down':
            death_screen.enabled = False
            main_menu.enabled = True
            game_state = 'menu'

app.run()