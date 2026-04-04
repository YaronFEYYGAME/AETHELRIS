import pygame
import random
from resource_manager import ResourceManager

class Enemy(pygame.sprite.Sprite):
    
    def __init__(self, x, y, name="ennemi", base_hp=100, base_dmg=10, base_speed=2.0, scale=1.5):
        super().__init__()
        self.name = name
        
        # --- STATS DE BASE ---
        self.max_health = base_hp
        self.health = self.max_health
        self.damage = base_dmg
        self.speed = base_speed
        
        # --- GESTION DES ANIMATIONS ---
        self.scale_factor = scale 
        self.animations = {'right': {}, 'left': {}}
        self.state = 'idle'
        self.frame_index = 0
        self.animation_speed = 0.2
        
        # On ne charge plus d'image d'Orc en dur ici !
        # Les sous-classes s'en chargeront.
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA) # Image temporaire transparente
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        
        # --- HITBOX ---
        hitbox_size = 10 * self.scale_factor
        self.feet = pygame.Rect(0, 0, hitbox_size, hitbox_size)
        
        self.position = pygame.math.Vector2(x, y)
        self.feet.midbottom = (round(self.position.x), round(self.position.y))
        
        # --- COMBAT ---
        self.is_dead = False
        self.death_time = 0
        self.is_attacking = False
        self.last_attack_time = 0
        self.attack_range = 40           # distance d'attaque (pixels)
        self.detection_radius = 200      # distance de détection du joueur
        self.damage_amount = base_dmg    # dégâts infligés au joueur

        # --- DIRECTION & MOUVEMENT ---
        self.facing = 'right'
        self.current_velocity = pygame.math.Vector2(0, 0)
        self.empty_space_below = int(43 * scale)  # espace vide sous le sprite
        self.slide_dir_x = 1
        self.slide_dir_y = 1

        # --- EFFETS DE STATUT ---
        self.paralyzed = False
        self.paralyze_end_time = 0
        self._zhonya_gold = False

        # --- SYSTÈME DE CACHE ET STATUTS ---
        self._tint_cache = {}
        self._blue_cache = {}
        self._gold_cache = {}
        self.is_stunned = False
        self.stun_end_time = 0
        self._is_blinking = False
        self.hit_time = 0

    # ---------------------------------------------------------
    # Ajoute ces méthodes utilitaires juste en dessous du __init__
    # ---------------------------------------------------------

    def load_dynamic_animation(self, anim_name, path):
        """Charge une animation en déduisant le nombre de frames."""
        try:
            sheet = ResourceManager.get_image(path)
            frame_size = sheet.get_height() 
            num_frames = sheet.get_width() // frame_size
            # On appelle ta méthode existante load_animation (qui doit toujours être dans ta classe)
            self.load_animation(anim_name, path, num_frames)
        except Exception as e:
            print(f"⚠️ Impossible de charger {path} pour {self.name} : {e}")

    def get_tinted_frame(self, base_frame, color_type):
        """Récupère ou crée une frame teintée mise en cache pour optimiser les FPS."""
        cache_key = (id(base_frame), color_type)
        if cache_key not in self._tint_cache:
            frame_copy = base_frame.copy()
            mask = pygame.mask.from_surface(frame_copy)
            
            if color_type == 'red':
                overlay = mask.to_surface(setcolor=(255, 0, 0, 150), unsetcolor=(0, 0, 0, 0))
            elif color_type == 'gray':
                overlay = mask.to_surface(setcolor=(100, 100, 100, 180), unsetcolor=(0, 0, 0, 0))
            elif color_type == 'gold':
                overlay = mask.to_surface(setcolor=(255, 215, 0, 150), unsetcolor=(0, 0, 0, 0))
            else:
                return base_frame
                
            frame_copy.blit(overlay, (0, 0))
            self._tint_cache[cache_key] = frame_copy
            
        return self._tint_cache[cache_key]

    def apply_stun(self, duration=3000):
        self.is_stunned = True
        self.stun_end_time = pygame.time.get_ticks() + duration

    def load_animation(self, state_name, path, num_frames):
        try:
            sprite_sheet = ResourceManager.get_image(path)
            frame_width = sprite_sheet.get_width() // num_frames
            frame_height = sprite_sheet.get_height()

            frames_right = []
            frames_left = []

            for i in range(num_frames):
                frame = sprite_sheet.subsurface((i * frame_width, 0, frame_width, frame_height))

                new_width = int(frame_width * self.scale_factor)
                new_height = int(frame_height * self.scale_factor)
                frame = pygame.transform.scale(frame, (new_width, new_height))

                frames_right.append(frame)
                frames_left.append(pygame.transform.flip(frame, True, False))

            self.animations['right'][state_name] = frames_right
            self.animations['left'][state_name] = frames_left
        except FileNotFoundError:
            print(f"⚠️ Erreur: Fichier {path} introuvable.")

    def paralyze(self, duration_ms):
        """Paralyse l'ennemi pour une durée donnée (en ms). Réinitialise si déjà paralysé."""
        self.paralyzed = True
        self.paralyze_end_time = pygame.time.get_ticks() + duration_ms

    def _get_blue_tinted(self, frame):
        """Retourne une version teintée en bleu du frame, mise en cache."""
        frame_id = id(frame)
        if frame_id in self._blue_cache:
            return self._blue_cache[frame_id]
        tinted = frame.copy()
        tinted.fill((100, 150, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._blue_cache[frame_id] = tinted
        return tinted

    def _get_gold_tinted(self, frame):
        """Retourne une version teintée en doré du frame, mise en cache."""
        frame_id = id(frame)
        if frame_id in self._gold_cache:
            return self._gold_cache[frame_id]
        tinted = frame.copy()
        tinted.fill((255, 200, 50, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._gold_cache[frame_id] = tinted
        return tinted

    def damage(self, amount):
        if self.is_dead: return 
        
        self.health -= amount
        self.hit_time = pygame.time.get_ticks() 
        
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.frame_index = 0 
            self.death_time = pygame.time.get_ticks() 

    def animate(self):
        if self.is_dead:
            self.state = 'death'
        elif self.is_attacking:
            self.state = 'attack'
        elif hasattr(self, 'current_velocity') and self.current_velocity.length() > 0.1:
            self.state = 'walk'
        else:
            self.state = 'idle'

        animation = self.animations[self.facing][self.state]

        # Paralysie : frame figée + teinte bleue
        if self.paralyzed:
            idx = max(0, min(int(self.frame_index), len(animation) - 1))
            if self._zhonya_gold:
                self.image = self._get_gold_tinted(animation[idx])
            else:
                self.image = self._get_blue_tinted(animation[idx])
            return

        speed = self.animation_speed
        if self.state == 'attack': speed *= 1.5

        self.frame_index += speed

        if self.frame_index >= len(animation):
            if self.state == 'death':
                self.frame_index = len(animation) - 1
            elif self.state == 'attack':
                self.is_attacking = False
                self.frame_index = 0
            else:
                self.frame_index = 0

        self.image = animation[int(self.frame_index)]

        if not self.is_dead and pygame.time.get_ticks() - self.hit_time < 150:
            self.image = self.image.copy()
            self.image.fill((255, 50, 50, 255), special_flags=pygame.BLEND_RGBA_MULT)

    def update(self, player, walls):
        if self.is_dead:
            self.animate()
            if pygame.time.get_ticks() - self.death_time > 3000:
                self.kill()
            return

        # Paralysie : figé, pas de mouvement ni d'attaque
        if self.paralyzed:
            if pygame.time.get_ticks() >= self.paralyze_end_time:
                self.paralyzed = False
                self._zhonya_gold = False
            else:
                self.current_velocity = pygame.math.Vector2(0, 0)
                self.animate()
                return

        target_center = pygame.math.Vector2(player.feet.center)
        my_center = pygame.math.Vector2(self.feet.center)
        target_vector = target_center - my_center
        distance = target_vector.length()

        velocity_x, velocity_y = 0, 0
        hit_x, hit_y = False, False

        if distance < self.detection_radius and distance > 0 and not self.is_attacking:
            norm_dir = target_vector.normalize()
            velocity_x = norm_dir.x * self.speed
            velocity_y = norm_dir.y * self.speed
            
            if velocity_x > 0.1: self.facing = "right"
            elif velocity_x < -0.1: self.facing = "left"

            # --- MOUVEMENT X ---
            self.position.x += velocity_x
            self.feet.centerx = round(self.position.x)
            for wall in walls:
                if self.feet.colliderect(wall):
                    if velocity_x > 0: self.feet.right = wall.left
                    elif velocity_x < 0: self.feet.left = wall.right
                    self.position.x = self.feet.centerx
                    hit_x = True
                    break
            
            # --- MOUVEMENT Y ---
            self.position.y += velocity_y
            self.feet.bottom = round(self.position.y)
            for wall in walls:
                if self.feet.colliderect(wall):
                    if velocity_y > 0: self.feet.bottom = wall.top
                    elif velocity_y < 0: self.feet.top = wall.bottom
                    self.position.y = self.feet.bottom
                    hit_y = True
                    break

            # --- IA : CONTOURNEMENT ---
            if hit_x and abs(norm_dir.y) < 0.5:
                self.position.y += self.speed * self.slide_dir_y
                self.feet.bottom = round(self.position.y)
                for wall in walls:
                    if self.feet.colliderect(wall):
                        self.position.y -= self.speed * self.slide_dir_y
                        self.slide_dir_y *= -1
                        self.position.y += self.speed * self.slide_dir_y
                        self.feet.bottom = round(self.position.y)
                        for w2 in walls:
                            if self.feet.colliderect(w2):
                                self.position.y -= self.speed * self.slide_dir_y
                                break
                        break
                self.feet.bottom = round(self.position.y)

            elif hit_y and abs(norm_dir.x) < 0.5:
                self.position.x += self.speed * self.slide_dir_x
                self.feet.centerx = round(self.position.x)
                for wall in walls:
                    if self.feet.colliderect(wall):
                        self.position.x -= self.speed * self.slide_dir_x
                        self.slide_dir_x *= -1
                        self.position.x += self.speed * self.slide_dir_x
                        self.feet.centerx = round(self.position.x)
                        for w2 in walls:
                            if self.feet.colliderect(w2):
                                self.position.x -= self.speed * self.slide_dir_x
                                break
                        break
                self.feet.centerx = round(self.position.x)

        self.current_velocity = pygame.math.Vector2(velocity_x, velocity_y)
        
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom + self.empty_space_below

        self.animate()

        if distance < self.attack_range and not self.is_attacking:
            current_time = pygame.time.get_ticks()
            if current_time - self.last_attack_time > 1500:
                self.last_attack_time = current_time
                self.is_attacking = True
                self.frame_index = 0
                player.damage(self.damage_amount, source_enemy=self)





# =====================================================================
# --- ENNEMI DISTANT (MULTIJOUEUR CLIENT) ---
# =====================================================================

class RemoteEnemy(pygame.sprite.Sprite):
    """Sprite ennemi piloté par l'état réseau côté client. Pas d'IA, rendu seul."""

    _CONFIGS = {
        'enemy': {
            'scale': 1.5,
            'empty_below': 43 * 1.5,
            'anims': [
                ('idle',   "assets/images/Orc-Idle.png",    6, 'strip'),
                ('walk',   "assets/images/Orc-Walk.png",    8, 'strip'),
                ('attack', "assets/images/Orc-Attack01.png",6, 'strip'),
                ('death',  "assets/images/Orc-Death.png",   4, 'strip'),
            ],
        },
        'bigenemy': {
            'scale': 3.5,
            'empty_below': 12 * 3.5,
            'anims': [
                ('idle',   "assets/images/idle.png",   5, 'vstrip'),
                ('run',    "assets/images/run.png",    8, 'vstrip'),
                ('attack', "assets/images/attack.png", 8, 'vstrip'),
                ('hit',    "assets/images/hit.png",    2, 'vstrip'),
                ('death',  "assets/images/death.png",  5, 'vstrip'),
            ],
        },
        'necromancer': {
            'scale': 2.0,
            'empty_below': 25 * 2.0,
            'anims': [
                ('idle',   "assets/images/necromancer_idle.png",       4,  'grid', 5, 1),
                ('run',    "assets/images/necromancer_idle2.png",       8,  'grid', 4, 2),
                ('attack', "assets/images/necromancer_attacking.png",  13, 'grid', 6, 3),
                ('skill',  "assets/images/necromancer_skill1.png",    12, 'grid', 6, 2),
                ('death',  "assets/images/necromancer_death.png",      20, 'grid', 10, 2),
            ],
        },
        'spirit': {
            'scale': 1.0,
            'empty_below': 10 * 1.0,
            'anims': [
                ('appear', "assets/images/necromancer_summonAppear.png", 6, 'grid', 3, 2),
                ('idle',   "assets/images/necromancer_summonIdle.png",   4, 'grid', 4, 1),
                ('run',    "assets/images/necromancer_summonIdle.png",   4, 'grid', 4, 1),
                ('death',  "assets/images/necromancer_summonDeath.png",  6, 'grid', 3, 2),
            ],
        },
        'medusa': {
            'scale': 1.0,
            'empty_below': 8,
            'anims': [
                ('idle',    "assets/images/Medusa_boss/Idle.png",     7,  'strip'),
                ('walk',    "assets/images/Medusa_boss/Walk.png",     13, 'strip'),
                ('run',     "assets/images/Medusa_boss/Run.png",      7,  'strip'),
                ('attack1', "assets/images/Medusa_boss/Attack_1.png", 16, 'strip'),
                ('attack2', "assets/images/Medusa_boss/Attack_2.png", 7,  'strip'),
                ('special', "assets/images/Medusa_boss/Special.png",  5,  'strip'),
                ('hurt',    "assets/images/Medusa_boss/Hurt.png",     3,  'strip'),
                ('death',   "assets/images/Medusa_boss/Dead.png",     3,  'strip'),
            ],
        },
    }

    def __init__(self, etype='enemy'):
        super().__init__()
        cfg = self._CONFIGS.get(etype, self._CONFIGS['enemy'])
        self.scale_factor = cfg['scale']
        self.empty_below = cfg['empty_below']
        self.animations = {'right': {}, 'left': {}}

        for anim_def in cfg['anims']:
            name, path, num_frames, mode = anim_def[0], anim_def[1], anim_def[2], anim_def[3]
            if mode == 'strip':
                self._load_strip(name, path, num_frames)
            elif mode == 'vstrip':
                self._load_vstrip(name, path, num_frames)
            else:
                cols, rows = anim_def[4], anim_def[5]
                self._load_grid(name, path, cols, rows, num_frames)

        first_state = cfg['anims'][0][0]
        self.image = self.animations['right'][first_state][0]
        self.rect = self.image.get_rect()

        hitbox_size = 10 * self.scale_factor
        self.feet = pygame.Rect(0, 0, hitbox_size, hitbox_size)
        self.feet.topleft = (0, 0)
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom + int(self.empty_below)

        self.health = 1
        self.max_health = 1
        self._blue_cache = {}

    def _get_blue_tinted(self, frame):
        frame_id = id(frame)
        if frame_id in self._blue_cache:
            return self._blue_cache[frame_id]
        tinted = frame.copy()
        tinted.fill((100, 150, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._blue_cache[frame_id] = tinted
        return tinted

    def _load_strip(self, state_name, path, num_frames):
        try:
            sheet = ResourceManager.get_image(path)
            fw = sheet.get_width() // num_frames
            fh = sheet.get_height()
            rights, lefts = [], []
            for i in range(num_frames):
                frame = sheet.subsurface((i * fw, 0, fw, fh))
                nw, nh = int(fw * self.scale_factor), int(fh * self.scale_factor)
                frame = pygame.transform.scale(frame, (nw, nh))
                rights.append(frame)
                lefts.append(pygame.transform.flip(frame, True, False))
            self.animations['right'][state_name] = rights
            self.animations['left'][state_name] = lefts
        except FileNotFoundError:
            pass

    def _load_vstrip(self, state_name, path, num_frames):
        """Charge un sprite sheet vertical (frames empilées en lignes)."""
        try:
            sheet = ResourceManager.get_image(path)
            fw = sheet.get_width()
            fh = sheet.get_height() // num_frames
            rights, lefts = [], []
            for i in range(num_frames):
                frame = sheet.subsurface((0, i * fh, fw, fh))
                nw, nh = int(fw * self.scale_factor), int(fh * self.scale_factor)
                frame = pygame.transform.scale(frame, (nw, nh))
                rights.append(frame)
                lefts.append(pygame.transform.flip(frame, True, False))
            self.animations['right'][state_name] = rights
            self.animations['left'][state_name] = lefts
        except FileNotFoundError:
            pass

    def _load_grid(self, state_name, path, cols, rows, num_frames):
        try:
            sheet = ResourceManager.get_image(path)
            fw = sheet.get_width() // cols
            fh = sheet.get_height() // rows
            rights, lefts = [], []
            count = 0
            for row in range(rows):
                for col in range(cols):
                    if count >= num_frames:
                        break
                    frame = sheet.subsurface((col * fw, row * fh, fw, fh))
                    nw, nh = int(fw * self.scale_factor), int(fh * self.scale_factor)
                    frame = pygame.transform.scale(frame, (nw, nh))
                    rights.append(frame)
                    lefts.append(pygame.transform.flip(frame, True, False))
                    count += 1
            self.animations['right'][state_name] = rights
            self.animations['left'][state_name] = lefts
        except FileNotFoundError:
            pass

    def update_from_state(self, state):
        x, y = state.get('x', self.feet.centerx), state.get('y', self.feet.bottom)
        direction = state.get('direction', 'right')
        anim_state = state.get('state', 'idle')
        frame = state.get('frame', 0)
        self.health = state.get('health', 1)
        self.max_health = state.get('max_health', 1)

        self.feet.midbottom = (round(x), round(y))
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom + int(self.empty_below)

        anims = self.animations.get(direction, self.animations['right'])
        if anim_state not in anims:
            anim_state = list(anims.keys())[0] if anims else 'idle'
        if anim_state in anims and anims[anim_state]:
            frames = anims[anim_state]
            self.image = frames[int(frame) % len(frames)]
            if state.get('paralyzed', False):
                self.image = self._get_blue_tinted(self.image)

    def update(self):
        pass


# =====================================================================
# --- FÉES (PNJ DE SOIN) ---
# =====================================================================

class Fairy(pygame.sprite.Sprite):
    """PNJ fée de soin. Ne bouge pas, joue son idle en boucle.
    Soigne le joueur une fois par joueur quand il interagit avec F."""

    FAIRY_SPRITES = {
        1: "assets/images/Fairy/Fairy 1.png",
        2: "assets/images/Fairy/Fairy 2.png",
        3: "assets/images/Fairy/Fairy 3.png",
    }

    def __init__(self, x, y, fairy_type=1):
        super().__init__()
        self.fairy_type = fairy_type
        self.scale_factor = 1.5
        self.frame_index = 0
        self.animation_speed = 0.12

        # Charger le spritesheet (horizontal, 8 frames de 32×32)
        self.frames = []
        try:
            path = self.FAIRY_SPRITES.get(fairy_type, self.FAIRY_SPRITES[1])
            sheet = ResourceManager.get_image(path)
            fw = sheet.get_width() // 8
            fh = sheet.get_height()
            for i in range(8):
                frame = sheet.subsurface((i * fw, 0, fw, fh))
                scaled = pygame.transform.scale(frame,
                    (int(fw * self.scale_factor), int(fh * self.scale_factor)))
                self.frames.append(scaled)
        except Exception:
            fallback = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(fallback, (100, 255, 100, 200), (16, 16), 12)
            self.frames = [fallback]

        self.image = self.frames[0]
        self.rect = self.image.get_rect()
        self.feet = pygame.Rect(0, 0, 16, 16)

        self.position = pygame.math.Vector2(x, y)
        self.feet.midbottom = (round(self.position.x), round(self.position.y))
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom + 8

        # Tracking des joueurs déjà soignés (par index: 0=host, 1=client)
        self.healed_players = set()

        # Dialogue
        self.in_dialogue = False
        self.dialogue_text = None
        self.dialogue_start_time = 0
        self.dialogue_duration = 4000
        self.dialogue_target_player = None

    def can_heal(self, player_index):
        """Vérifie si la fée peut encore soigner ce joueur."""
        return player_index not in self.healed_players

    def interact(self, player, player_index):
        """Interaction avec la fée. Retourne le texte de dialogue."""
        if self.in_dialogue:
            return None

        self.in_dialogue = True
        self.dialogue_start_time = pygame.time.get_ticks()
        self.dialogue_target_player = player_index

        if self.can_heal(player_index):
            self.healed_players.add(player_index)
            player.health = player.max_health
            self.dialogue_text = "Hop ! Tes ecorchures ne sont plus qu'un mauvais souvenir. Essaie de ne pas te briser en mille morceaux avant notre prochaine rencontre !"
        else:
            self.dialogue_text = "Oups ! La source est a sec et mes mains tremblent. Il va falloir faire preuve d'un peu plus de prudence, petit mortel."

        return self.dialogue_text

    def skip_dialogue(self):
        """Skip le dialogue en cours."""
        if self.in_dialogue:
            self.in_dialogue = False
            self.dialogue_text = None
            return True
        return False

    def get_current_dialogue(self):
        """Retourne le texte du dialogue en cours."""
        if self.in_dialogue:
            return self.dialogue_text
        return None

    def update(self, *args):
        # Animation idle en boucle
        self.frame_index += self.animation_speed
        if self.frame_index >= len(self.frames):
            self.frame_index = 0
        self.image = self.frames[int(self.frame_index)]

        # Fin automatique du dialogue
        if self.in_dialogue:
            if pygame.time.get_ticks() - self.dialogue_start_time >= self.dialogue_duration:
                self.in_dialogue = False
                self.dialogue_text = None


