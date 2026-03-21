import pygame
from projectile import Projectile

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.scale_factor = 1.5 
        self.animations = {'right': {}, 'left': {}}
        self.state = 'idle'
        self.frame_index = 0
        self.animation_speed = 0.2 
        
        self.empty_space_below = 43 * self.scale_factor 
        
        self.load_animation('idle', "assets/images/Soldier-Idle.png", 6)
        self.load_animation('walk', "assets/images/Soldier-Walk.png", 8)
        self.load_animation('death', "assets/images/Soldier-Death.png", 4)
        self.load_animation('attack_melee', "assets/images/Soldier-Attack01.png", 6)
        self.load_animation('attack_ranged', "assets/images/Soldier-Attack03.png", 9)
        
        self.image = self.animations['right']['idle'][0]
        self.rect = self.image.get_rect()
        
        hitbox_size = 10 * self.scale_factor 
        self.feet = pygame.Rect(0, 0, hitbox_size, hitbox_size)
        
        self.position = pygame.math.Vector2(x, y)
        self.feet.midbottom = (round(self.position.x), round(self.position.y))
        
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom 

        self.velocity = pygame.math.Vector2(0, 0)
        self.speed = 2.5
        self.max_health = 100
        self.health = 100

        self.attack_cooldown = 600 
        self.last_attack_time = 0
        self.melee_damage = 10
        self.facing = "right" 
        self.is_attacking = False 
        self.arrow_fired = False

        self.has_melee = False
        self.has_ranged = False
        self.current_weapon = None 
        self.has_pickaxe = False
        self.arrows = 0
        
        # --- NOUVEAU : INVENTAIRE BOTTES & COOLDOWN ---
        self.has_boots = False
        self.dash_cooldown = 4000
        self.last_dash_time = 0

        self.is_hit = False
        self.last_hit_time = 0

    def load_animation(self, state_name, path, num_frames):
        try:
            sprite_sheet = pygame.image.load(path).convert_alpha()
            frame_width = sprite_sheet.get_width() // num_frames
            frame_height = sprite_sheet.get_height()
            frames_right = []
            frames_left = []
            for i in range(num_frames):
                frame = sprite_sheet.subsurface((i * frame_width, 0, frame_width, frame_height))
                new_width = int(frame_width * self.scale_factor)
                new_height = int(frame_height * self.scale_factor)
                frame = pygame.transform.scale(frame, (new_width, new_height))
                
                shifted_frame = pygame.Surface((new_width, new_height), pygame.SRCALPHA)
                shifted_frame.blit(frame, (0, int(self.empty_space_below)))
                
                frames_right.append(shifted_frame)
                frames_left.append(pygame.transform.flip(shifted_frame, True, False))
            self.animations['right'][state_name] = frames_right
            self.animations['left'][state_name] = frames_left
        except FileNotFoundError:
            print(f"⚠️ Erreur: Fichier {path} introuvable.")

    def switch_weapon(self, weapon_name):
        if weapon_name == 'melee' and self.has_melee:
            self.current_weapon = 'melee'
        elif weapon_name == 'ranged' and self.has_ranged:
            self.current_weapon = 'ranged'

    def input(self):
        if self.state == 'death' or self.is_attacking:
            self.velocity.xy = 0, 0
            return 
            
        keys = pygame.key.get_pressed()
        self.velocity.xy = 0, 0 

        if keys[pygame.K_z]: self.velocity.y -= 1
        elif keys[pygame.K_s]: self.velocity.y += 1
        if keys[pygame.K_q]: 
            self.velocity.x -= 1
            self.facing = "left"  
        elif keys[pygame.K_d]: 
            self.velocity.x += 1
            self.facing = "right" 

        if self.velocity.length() > 0:
            self.velocity = self.velocity.normalize() * self.speed

    def move(self, walls):
        if self.state == 'death' or self.is_attacking:
            return

        self.position.x += self.velocity.x
        self.feet.centerx = round(self.position.x)
        for wall in walls:
            if self.feet.colliderect(wall):
                if self.velocity.x > 0: self.feet.right = wall.left
                elif self.velocity.x < 0: self.feet.left = wall.right
                self.position.x = self.feet.centerx

        self.position.y += self.velocity.y
        self.feet.bottom = round(self.position.y)
        for wall in walls:
            if self.feet.colliderect(wall):
                if self.velocity.y > 0: self.feet.bottom = wall.top
                elif self.velocity.y < 0: self.feet.top = wall.bottom
                self.position.y = self.feet.bottom

        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom 

    # --- NOUVEAU : LA FONCTION DE DASH SÉCURISÉE ---
    def dash(self, walls):
        current_time = pygame.time.get_ticks()
        # Vérifie si le cooldown est passé
        if current_time - self.last_dash_time < self.dash_cooldown:
            return False
            
        self.last_dash_time = current_time
        dash_distance = 150 # Distance de la téléportation
        step = 10 # On vérifie les collisions tous les 10 pixels
        
        # Détermine la direction du dash (selon le mouvement ou le regard)
        if self.velocity.length() > 0:
            dir_vec = self.velocity.normalize()
        else:
            dir_vec = pygame.math.Vector2(1 if self.facing == 'right' else -1, 0)
            
        # Déplacement éclair avec vérification des murs
        for _ in range(int(dash_distance / step)):
            self.feet.x += dir_vec.x * step
            if any(self.feet.colliderect(w) for w in walls):
                self.feet.x -= dir_vec.x * step # On annule si mur touché
            else:
                self.position.x = self.feet.centerx
                
            self.feet.y += dir_vec.y * step
            if any(self.feet.colliderect(w) for w in walls):
                self.feet.y -= dir_vec.y * step
            else:
                self.position.y = self.feet.bottom
                
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom
        return True

    def animate(self):
        if self.health <= 0:
            self.state = 'death'
        elif self.is_attacking:
            if self.current_weapon == 'melee':
                self.state = 'attack_melee'
            elif self.current_weapon == 'ranged':
                self.state = 'attack_ranged'
        elif self.velocity.length() > 0:
            self.state = 'walk'
        else:
            self.state = 'idle'
            
        animation = self.animations[self.facing][self.state]
        speed = self.animation_speed * 1.5 if 'attack' in self.state else self.animation_speed
        self.frame_index += speed
        
        if self.frame_index >= len(animation):
            if self.state == 'death':
                self.frame_index = len(animation) - 1 
            elif 'attack' in self.state:
                self.is_attacking = False
                self.frame_index = 0
            else:
                self.frame_index = 0 
                
        self.image = animation[int(self.frame_index)].copy()
        
        if self.is_hit:
            if pygame.time.get_ticks() - self.last_hit_time < 200: 
                mask = pygame.mask.from_surface(self.image)
                red_overlay = mask.to_surface(setcolor=(255, 0, 0, 150), unsetcolor=(0, 0, 0, 0))
                self.image.blit(red_overlay, (0, 0))
            else:
                self.is_hit = False

    def attack(self):
        if self.state == 'death' or self.is_attacking or self.current_weapon is None:
            return None
            
        current_time = pygame.time.get_ticks()
        cooldown = 600 if self.current_weapon == 'melee' else 800

        if current_time - self.last_attack_time > cooldown:
            if self.current_weapon == 'ranged' and self.arrows <= 0:
                return None 
                
            self.last_attack_time = current_time
            self.is_attacking = True
            self.frame_index = 0 
            
            if self.current_weapon == 'melee':
                attack_size = 70 
                attack_rect = pygame.Rect(0, 0, attack_size, attack_size)
                attack_rect.center = self.feet.center
                return ('melee', attack_rect)
            elif self.current_weapon == 'ranged':
                self.arrow_fired = False
                return None
        return None

    def check_ranged_attack(self):
        if self.state == 'attack_ranged' and int(self.frame_index) == 6 and not self.arrow_fired:
            self.arrow_fired = True
            self.arrows -= 1 
            projectile = Projectile(self.feet.centerx, self.feet.centery, self.facing)
            return projectile
        return None

    def is_moving(self):
        return self.velocity.length() > 0
        
    def damage(self, amount):
        if self.state != 'death':
            self.health -= amount
            self.is_hit = True
            self.last_hit_time = pygame.time.get_ticks()
            
            if self.health <= 0: 
                self.health = 0
                self.frame_index = 0 

    def heal(self, amount):
        if self.state != 'death':
            self.health += amount
            if self.health > self.max_health:
                self.health = self.max_health
                
    def apply_network_inputs(self, inputs):
        """Pilote le joueur depuis des inputs réseau (dict) au lieu du clavier."""
        if self.state == 'death' or self.is_attacking:
            self.velocity.xy = 0, 0
            return
        self.velocity.xy = 0, 0
        if inputs.get('up'):
            self.velocity.y -= 1
        if inputs.get('down'):
            self.velocity.y += 1
        if inputs.get('left'):
            self.velocity.x -= 1
            self.facing = 'left'
        if inputs.get('right'):
            self.velocity.x += 1
            self.facing = 'right'
        if self.velocity.length() > 0:
            self.velocity = self.velocity.normalize() * self.speed

    def update(self):
        self.input()
        self.animate()


class RemotePlayer(pygame.sprite.Sprite):
    """Sprite du joueur distant : rendu uniquement, piloté par l'état réseau reçu."""

    def __init__(self, x, y):
        super().__init__()
        self.scale_factor = 1.5
        self.animations = {'right': {}, 'left': {}}
        self.empty_space_below = 43 * self.scale_factor

        self._load_anim('idle', "assets/images/Soldier-Idle.png", 6)
        self._load_anim('walk', "assets/images/Soldier-Walk.png", 8)
        self._load_anim('death', "assets/images/Soldier-Death.png", 4)
        self._load_anim('attack_melee', "assets/images/Soldier-Attack01.png", 6)
        self._load_anim('attack_ranged', "assets/images/Soldier-Attack03.png", 9)

        self.image = self.animations['right']['idle'][0]
        self.rect = self.image.get_rect()

        hitbox_size = 10 * self.scale_factor
        self.feet = pygame.Rect(0, 0, hitbox_size, hitbox_size)
        self.feet.midbottom = (round(x), round(y))
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom

        self.health = 100
        self.max_health = 100

    def _load_anim(self, state_name, path, num_frames):
        try:
            sheet = pygame.image.load(path).convert_alpha()
            fw = sheet.get_width() // num_frames
            fh = sheet.get_height()
            rights, lefts = [], []
            for i in range(num_frames):
                frame = sheet.subsurface((i * fw, 0, fw, fh))
                nw, nh = int(fw * self.scale_factor), int(fh * self.scale_factor)
                frame = pygame.transform.scale(frame, (nw, nh))
                shifted = pygame.Surface((nw, nh), pygame.SRCALPHA)
                shifted.blit(frame, (0, int(self.empty_space_below)))
                rights.append(shifted)
                lefts.append(pygame.transform.flip(shifted, True, False))
            self.animations['right'][state_name] = rights
            self.animations['left'][state_name] = lefts
        except FileNotFoundError:
            pass

    def update_from_state(self, state):
        x, y = state.get('x', self.feet.centerx), state.get('y', self.feet.bottom)
        direction = state.get('direction', 'right')
        anim_state = state.get('state', 'idle')
        frame = state.get('frame', 0)
        self.health = state.get('health', 100)
        self.max_health = state.get('max_health', 100)

        self.feet.midbottom = (round(x), round(y))
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom

        anims = self.animations.get(direction, self.animations['right'])
        if anim_state not in anims:
            anim_state = 'idle'
        frames = anims[anim_state]
        self.image = frames[int(frame) % len(frames)]

    def update(self):
        pass