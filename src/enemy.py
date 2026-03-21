import pygame

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        
        # --- GESTION DES ANIMATIONS ---
        self.scale_factor = 1.5 
        self.animations = {'right': {}, 'left': {}}
        self.state = 'idle'
        self.frame_index = 0
        self.animation_speed = 0.2
        
        self.load_animation('idle', "assets/images/Orc-Idle.png", 6)
        self.load_animation('walk', "assets/images/Orc-Walk.png", 8)
        self.load_animation('attack', "assets/images/Orc-Attack01.png", 6)
        self.load_animation('death', "assets/images/Orc-Death.png", 4)

        self.image = self.animations['right']['idle'][0]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        
        # --- HITBOX ---
        hitbox_size = 10 * self.scale_factor
        self.feet = pygame.Rect(0, 0, hitbox_size, hitbox_size)
        
        self.position = pygame.math.Vector2(x, y)
        self.feet.midbottom = (round(self.position.x), round(self.position.y))
        
        self.empty_space_below = 43 * self.scale_factor 
        
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom + self.empty_space_below

        # --- STATS ---
        self.speed = 1.2 
        self.max_health = 30
        self.health = 30
        
        # --- IA & COMBAT ---
        self.detection_radius = 120 
        self.attack_range = 40
        self.damage_amount = 10
        self.last_attack_time = 0
        
        self.facing = "right"
        self.is_attacking = False
        
        # --- GESTION DES DÉGÂTS (CLIGNOTEMENT & MORT) ---
        self.is_dead = False 
        self.death_time = 0 
        self.hit_time = 0
        
        self.slide_dir_x = 1
        self.slide_dir_y = 1
        
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
                
                frames_right.append(frame)
                frames_left.append(pygame.transform.flip(frame, True, False))
                
            self.animations['right'][state_name] = frames_right
            self.animations['left'][state_name] = frames_left
        except FileNotFoundError:
            print(f"⚠️ Erreur: Fichier {path} introuvable.")
            
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
                player.damage(self.damage_amount)


class BigEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.scale_factor = 2.5 
        self.animations = {'right': {}, 'left': {}}
        self.state = 'idle'
        self.frame_index = 0
        self.animation_speed = 0.15 
        
        self.load_animation('idle', "assets/images/idle.png", 5)
        self.load_animation('run', "assets/images/run.png", 8)
        self.load_animation('attack', "assets/images/attack.png", 8)
        self.load_animation('hit', "assets/images/hit.png", 2)
        self.load_animation('death', "assets/images/death.png", 5)
        
        self.image = self.animations['right']['idle'][0]
        self.rect = self.image.get_rect()
        
        hitbox_width = int(20 * self.scale_factor)
        hitbox_height = int(12 * self.scale_factor) 
        self.feet = pygame.Rect(0, 0, hitbox_width, hitbox_height)
        
        self.y_offset = int(12 * self.scale_factor) 
        
        self.position = pygame.math.Vector2(x, y)
        self.feet.midbottom = (round(self.position.x), round(self.position.y))
        
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom + self.y_offset 
        
        self.max_health = 390  
        self.health = 390      
        self.speed = 0.9       
        self.damage_amount = 7.5 
        
        self.aggro_radius = 300 
        
        self.velocity = pygame.math.Vector2(0, 0)
        self.facing = "right"
        
        self.is_attacking = False
        self.last_attack_time = 0
        self.attack_cooldown = 1500
        self._is_blinking = False

        self.slide_dir_x = 1
        self.slide_dir_y = 1
        
        self.has_dealt_damage_1 = False
        self.has_dealt_damage_2 = False
        self.has_aggro = False
        self.pending_drop = None
        
        # Sons gérés via pending_sounds → SpatialAudioManager dans game.py
        self.activation_played = False
        self.death_sound_played = False
        self.last_talk_time = 0

        self.talk_cooldown = 8000
        self.talk_count = 0
        self.max_talks = 3
        self.bgm_playing = False
        self.pending_sounds = []

    def load_animation(self, state_name, path, num_frames):
        try:
            sprite_sheet = pygame.image.load(path).convert_alpha()
            frame_width = sprite_sheet.get_width()
            frame_height = sprite_sheet.get_height() // num_frames
            
            frames_right = []
            frames_left = []
            for i in range(num_frames):
                frame = sprite_sheet.subsurface((0, i * frame_height, frame_width, frame_height))
                new_width = int(frame_width * self.scale_factor)
                new_height = int(frame_height * self.scale_factor)
                frame = pygame.transform.scale(frame, (new_width, new_height))
                
                frames_right.append(frame)
                frames_left.append(pygame.transform.flip(frame, True, False))
                
            self.animations['right'][state_name] = frames_right
            self.animations['left'][state_name] = frames_left
        except FileNotFoundError:
            print(f"⚠️ Erreur: Fichier {path} introuvable.")

    def damage(self, amount):
        if self.health > 0 and self.state != 'hit':
            self.health -= amount
            self._is_blinking = True
            
            import random
            if random.randint(1, 100) <= 15:
                self.pending_drop = random.choice(['apple', 'arrow'])
            
            if self.health <= 0:
                self.health = 0
                self.state = 'death'
                self.frame_index = 0
                self.is_attacking = False
                self.velocity.xy = 0, 0
                self._is_blinking = False
                
                if not self.death_sound_played:
                    self.death_sound_played = True
                    self.pending_sounds.append('boss_death')

                if self.bgm_playing:
                    self.bgm_playing = False
                    self.pending_sounds.append('boss_bgm_stop')
            else:
                self.state = 'hit'
                self.frame_index = 0
                self.is_attacking = False 
                self.velocity.xy = 0, 0 

    def update(self, player, walls):
        if self.state == 'death':
            self.animate()
            return

        current_time = pygame.time.get_ticks()
        
        target_center = pygame.math.Vector2(player.feet.center)
        my_center = pygame.math.Vector2(self.feet.center)
        target_vector = target_center - my_center
        distance = target_vector.length()

        if distance < self.aggro_radius and player.health > 0:
            if not self.has_aggro:
                self.has_aggro = True
                if not self.activation_played:
                    self.activation_played = True
                    self.pending_sounds.append('boss_activation')

                if not self.bgm_playing:
                    self.bgm_playing = True
                    self.pending_sounds.append('boss_bgm_start')

        elif player.health <= 0:
            self.has_aggro = False
            if self.bgm_playing:
                self.bgm_playing = False
                self.pending_sounds.append('boss_bgm_stop')

        if self.has_aggro and self.health > 0 and self.talk_count < self.max_talks and player.health > 0:
            if current_time - self.last_talk_time > self.talk_cooldown:
                import random
                if random.randint(1, 150) <= 1:
                    self.pending_sounds.append('boss_talk')
                    self.last_talk_time = current_time
                    self.talk_count += 1

        hit_x = False
        hit_y = False
        norm_dir = pygame.math.Vector2(0, 0)

        if self.state == 'hit':
            self.velocity.xy = 0, 0 
        
        elif self.is_attacking:
            self.velocity.xy = 0, 0 
            current_frame = int(self.frame_index)
            
            if current_frame == 1 and not self.has_dealt_damage_1:
                attack_area = self.get_attack_hitbox()
                if attack_area.colliderect(player.feet.inflate(20, 20)) and player.health > 0:
                    player.damage(self.damage_amount)
                    self.health = min(self.max_health, self.health + (self.damage_amount * 0.3))
                self.has_dealt_damage_1 = True 
                
            elif current_frame == 5 and not self.has_dealt_damage_2:
                self.pending_sounds.append('boss_attack')

                attack_area = self.get_attack_hitbox()
                if attack_area.colliderect(player.feet.inflate(20, 20)) and player.health > 0:
                    player.damage(self.damage_amount)
                    self.health = min(self.max_health, self.health + (self.damage_amount * 0.3))
                self.has_dealt_damage_2 = True
        
        else:
            if player.health > 0:
                if player.feet.centerx > self.feet.centerx: self.facing = 'right'
                else: self.facing = 'left'

                attack_area = self.get_attack_hitbox()
                
                if attack_area.colliderect(player.feet.inflate(20, 20)):
                    if current_time - self.last_attack_time > self.attack_cooldown:
                        self.is_attacking = True
                        self.state = 'attack'
                        self.frame_index = 0
                        self.last_attack_time = current_time
                        self.has_dealt_damage_1 = False
                        self.has_dealt_damage_2 = False
                        self.velocity.xy = 0, 0
                        
                        self.pending_sounds.append('boss_attack')
                    else:
                        self.state = 'idle'
                        self.velocity.xy = 0, 0

                elif distance < self.aggro_radius and distance > 0:
                    self.state = 'run'
                    norm_dir = target_vector.normalize()
                    self.velocity.x = norm_dir.x * self.speed
                    self.velocity.y = norm_dir.y * self.speed
                else:
                    self.state = 'idle'
                    self.velocity.xy = 0, 0
            else:
                self.state = 'idle'
                self.velocity.xy = 0, 0

        if self.state == 'run':
            self.position.x += self.velocity.x
            self.feet.centerx = round(self.position.x)
            for wall in walls:
                if self.feet.colliderect(wall):
                    if self.velocity.x > 0: self.feet.right = wall.left
                    elif self.velocity.x < 0: self.feet.left = wall.right
                    self.position.x = self.feet.centerx
                    hit_x = True
                    break

            self.position.y += self.velocity.y
            self.feet.bottom = round(self.position.y)
            for wall in walls:
                if self.feet.colliderect(wall):
                    if self.velocity.y > 0: self.feet.bottom = wall.top
                    elif self.velocity.y < 0: self.feet.top = wall.bottom
                    self.position.y = self.feet.bottom
                    hit_y = True
                    break
                    
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
                    
            self.rect.centerx = self.feet.centerx
            self.rect.bottom = self.feet.bottom + self.y_offset 
            
        self.animate()

    def get_attack_hitbox(self):
        range_attack = 135
        width_attack = 18

        attack_rect = pygame.Rect(0, 0, range_attack, width_attack)

        if self.facing == 'right':
            attack_rect.left = self.feet.left - 10
        else:
            attack_rect.right = self.feet.right + 10

        # Ancrer le bas sur les pieds, hitbox étroite verticalement
        attack_rect.bottom = self.feet.centery + 15
        return attack_rect

    def animate(self):
        animation = self.animations[self.facing][self.state]
        
        speed = self.animation_speed
        if self.state in ['hit', 'death']: speed = 0.1
        
        self.frame_index += speed
        
        if self.frame_index >= len(animation):
            if self.state == 'death':
                self.frame_index = len(animation) - 1 
                self._is_blinking = False 
            elif self.state == 'hit':
                self.state = 'idle'
                self.frame_index = 0
                self._is_blinking = False 
            elif self.state == 'attack':
                self.is_attacking = False
                self.state = 'idle'
                self.frame_index = 0
            else:
                self.frame_index = 0
                
        animation = self.animations[self.facing][self.state]
        self.image = animation[int(self.frame_index)].copy()
        
        if self.state == 'death':
            self._is_blinking = False
            
        if self.state == 'hit' or self._is_blinking:
            mask = pygame.mask.from_surface(self.image)
            red_overlay = mask.to_surface(setcolor=(255, 0, 0, 150), unsetcolor=(0, 0, 0, 0))
            self.image.blit(red_overlay, (0, 0))
    
    def update_volumes(self, music_vol, sfx_vol):
        # Sons gérés via pending_sounds → SpatialAudioManager, rien à ajuster ici
        pygame.mixer.music.set_volume(music_vol)

# =====================================================================
# --- NOUVEAU BOSS : LE NÉCROMANCIEN ET SES ESPRITS ---
# =====================================================================

class Spirit(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.scale_factor = 1.0
        self.animations = {'right': {}, 'left': {}}
        self.state = 'appear'
        self.frame_index = 0
        self.animation_speed = 0.2
        
        self.load_grid_animation('appear', "assets/images/necromancer_summonAppear.png", 3, 2, 6)
        self.load_grid_animation('idle', "assets/images/necromancer_summonIdle.png", 4, 1, 4)
        self.load_grid_animation('run', "assets/images/necromancer_summonIdle.png", 4, 1, 4) 
        self.load_grid_animation('death', "assets/images/necromancer_summonDeath.png", 3, 2, 6)
        self.load_grid_animation('explode', "assets/images/explosion_anim.png", 5, 1, 5, scale_override=0.45)
        
        self.image = self.animations['right']['appear'][0]
        self.rect = self.image.get_rect()
        
        hitbox_w = int(15 * self.scale_factor)
        hitbox_h = int(12 * self.scale_factor) 
        self.feet = pygame.Rect(0, 0, hitbox_w, hitbox_h)
        
        self.y_offset = int(10 * self.scale_factor) 
        
        self.position = pygame.math.Vector2(x, y)
        self.feet.midbottom = (round(self.position.x), round(self.position.y))
        
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom + self.y_offset 
        
        self.health = 1 
        self.speed = 1.8 
        self.velocity = pygame.math.Vector2(0, 0)
        self.facing = "right"
        self.damage_amount = 15 

    def load_grid_animation(self, state_name, path, cols, rows, num_frames, scale_override=None):
        scale = scale_override if scale_override is not None else self.scale_factor
        try:
            sprite_sheet = pygame.image.load(path).convert_alpha()
            frame_width = sprite_sheet.get_width() // cols
            frame_height = sprite_sheet.get_height() // rows
            frames_right = []
            frames_left = []
            count = 0
            for row in range(rows):
                for col in range(cols):
                    if count >= num_frames: break
                    frame = sprite_sheet.subsurface((col * frame_width, row * frame_height, frame_width, frame_height))
                    new_width = int(frame_width * scale)
                    new_height = int(frame_height * scale)
                    frame = pygame.transform.scale(frame, (new_width, new_height))
                    frames_right.append(frame)
                    frames_left.append(pygame.transform.flip(frame, True, False))
                    count += 1
            self.animations['right'][state_name] = frames_right
            self.animations['left'][state_name] = frames_left
        except FileNotFoundError:
            print(f"⚠️ Erreur: Fichier {path} introuvable.")

    def damage(self, amount):
        if self.health > 0 and self.state not in ['death', 'explode']:
            self.health -= amount
            if self.health <= 0:
                self.state = 'death' 
                self.frame_index = 0
                self.velocity.xy = 0, 0

    def update(self, player, walls):
        if self.state in ['death', 'explode']:
            self.animate()
            if self.frame_index >= len(self.animations[self.facing][self.state]) - 1:
                self.kill() 
            return

        if self.state == 'appear':
            self.animate()
            if self.frame_index >= len(self.animations[self.facing]['appear']) - 1:
                self.state = 'run' 
            return

        target_center = pygame.math.Vector2(player.feet.center)
        my_center = pygame.math.Vector2(self.feet.center)
        target_vector = target_center - my_center
        distance = target_vector.length()

        if distance < 25 and player.health > 0:
            player.damage(self.damage_amount)
            self.state = 'explode'
            self.frame_index = 0
            self.velocity.xy = 0, 0
            self.explode_center = self.rect.center
        elif distance > 0 and player.health > 0:
            self.state = 'run'
            norm_dir = target_vector.normalize()
            self.velocity.x = norm_dir.x * self.speed
            self.velocity.y = norm_dir.y * self.speed
            if self.velocity.x > 0: self.facing = "right"
            elif self.velocity.x < 0: self.facing = "left"
        else:
            self.state = 'idle'
            self.velocity.xy = 0, 0

        self.position.x += self.velocity.x
        self.feet.centerx = round(self.position.x)
        self.position.y += self.velocity.y
        self.feet.bottom = round(self.position.y)
        
        self.animate()

    def animate(self):
        animation = self.animations[self.facing][self.state]
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            if self.state in ['death', 'appear', 'explode']:
                self.frame_index = len(animation) - 1
            else:
                self.frame_index = 0
        self.image = animation[int(self.frame_index)].copy()
        
        if self.state == 'explode':
            self.rect = self.image.get_rect()
            self.rect.center = self.explode_center
        else:
            self.rect.centerx = self.feet.centerx
            self.rect.bottom = self.feet.bottom + self.y_offset


class Necromancer(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.scale_factor = 2.0 
        self.animations = {'right': {}, 'left': {}}
        self.state = 'idle'
        self.frame_index = 0
        self.animation_speed = 0.15
        
        self.load_grid_animation('idle', "assets/images/necromancer_idle.png", 5, 1, 5)
        self.load_grid_animation('run', "assets/images/necromancer_idle2.png", 4, 2, 8)
        self.load_grid_animation('attack', "assets/images/necromancer_attacking.png", 6, 3, 13)
        self.load_grid_animation('skill', "assets/images/necromancer_skill1.png", 6, 2, 12)
        self.load_grid_animation('death', "assets/images/necromancer_death.png", 10, 2, 20)
        
        self.image = self.animations['right']['idle'][0]
        self.rect = self.image.get_rect()
        
        hitbox_width = int(26 * self.scale_factor)
        hitbox_height = int(38 * self.scale_factor)
        self.feet = pygame.Rect(0, 0, hitbox_width, hitbox_height)

        self.y_offset = int(25 * self.scale_factor)
        
        self.position = pygame.math.Vector2(x, y)
        self.feet.midbottom = (round(self.position.x), round(self.position.y))
        
        self.rect.centerx = self.feet.centerx 
        self.rect.bottom = self.feet.bottom + self.y_offset
        
        self.max_health = 450
        self.health = 450
        self.speed = 1.5
        self.damage_amount = 10
        self.aggro_radius = 400
        
        self.velocity = pygame.math.Vector2(0, 0)
        self.facing = "right"
        self.is_attacking = False
        self.last_attack_time = 0
        self.attack_cooldown = 1800
        
        self.last_skill_time = pygame.time.get_ticks()
        self.skill_cooldown = 18000 
        self.has_summoned = False
        self.pending_summons = [] 
        self.pending_drop = None
        
        self._is_blinking = False
        self.hit_time = 0
        self.has_dealt_damage_1 = False
        self.has_dealt_damage_2 = False
        self.has_aggro = False
        self.bgm_playing = False
        
        self.slide_dir_x = 1
        self.slide_dir_y = 1
        self.pending_sounds = []

        # Sons gérés via pending_sounds → SpatialAudioManager dans game.py

    def load_grid_animation(self, state_name, path, cols, rows, num_frames):
        try:
            sprite_sheet = pygame.image.load(path).convert_alpha()
            frame_width = sprite_sheet.get_width() // cols
            frame_height = sprite_sheet.get_height() // rows
            frames_right = []
            frames_left = []
            count = 0
            for row in range(rows):
                for col in range(cols):
                    if count >= num_frames: break
                    frame = sprite_sheet.subsurface((col * frame_width, row * frame_height, frame_width, frame_height))
                    new_width = int(frame_width * self.scale_factor)
                    new_height = int(frame_height * self.scale_factor)
                    frame = pygame.transform.scale(frame, (new_width, new_height))
                    frames_right.append(frame)
                    frames_left.append(pygame.transform.flip(frame, True, False))
                    count += 1
            self.animations['right'][state_name] = frames_right
            self.animations['left'][state_name] = frames_left
        except FileNotFoundError:
            print(f"⚠️ Erreur: Fichier {path} introuvable.")

    def damage(self, amount):
        if self.health > 0 and self.state != 'death':
            self.health -= amount
            self._is_blinking = True
            self.hit_time = pygame.time.get_ticks() 
            import random
            if random.randint(1, 100) <= 20:
                self.pending_drop = random.choice(['apple', 'arrow'])
            
            if self.health <= 0:
                self.health = 0
                self.state = 'death'
                self.frame_index = 0
                self.is_attacking = False
                self.velocity.xy = 0, 0
                self._is_blinking = False
                self.pending_sounds.append('boss_death')
                if self.bgm_playing:
                    self.bgm_playing = False
                    self.pending_sounds.append('boss_bgm_stop')

    def update(self, player, walls):
        if self.state == 'death':
            self.animate()
            return

        current_time = pygame.time.get_ticks()
        target_center = pygame.math.Vector2(player.feet.center)
        my_center = pygame.math.Vector2(self.feet.center)
        target_vector = target_center - my_center
        distance = target_vector.length()

        if distance < self.aggro_radius and player.health > 0:
            if not self.has_aggro:
                self.has_aggro = True
            if not self.bgm_playing:
                self.bgm_playing = True
                self.pending_sounds.append('boss_bgm_start')
        elif player.health <= 0:
            self.has_aggro = False
            self._is_blinking = False
            if self.bgm_playing:
                self.bgm_playing = False
                self.pending_sounds.append('boss_bgm_stop')

        hit_x = False
        hit_y = False
        norm_dir = pygame.math.Vector2(0, 0)
            
        if self.state == 'skill':
            self.velocity.xy = 0, 0
            current_frame = int(self.frame_index)
            if current_frame == 6 and not self.has_summoned:
                self.pending_summons.append((self.rect.centerx - 60, self.rect.centery + 20))
                self.pending_summons.append((self.rect.centerx + 60, self.rect.centery + 20))
                self.pending_summons.append((self.rect.centerx, self.rect.centery - 50))
                self.has_summoned = True
                
        elif self.is_attacking:
            self.velocity.xy = 0, 0
            current_frame = int(self.frame_index)
            # Frame 6 : la faux est au bas de son premier balayage (impact visuel)
            if current_frame == 6 and not self.has_dealt_damage_1:
                self.pending_sounds.append('boss_attack')
                attack_area = self.get_attack_hitbox(salve=1)
                if self._hits_player(attack_area, player) and player.health > 0:
                    player.damage(self.damage_amount)
                    self.health = min(self.max_health, self.health + (self.damage_amount * 0.5))
                self.has_dealt_damage_1 = True
            # Frame 11 : second balayage, faux au plus bas
            elif current_frame == 11 and not self.has_dealt_damage_2:
                self.pending_sounds.append('boss_attack')
                attack_area = self.get_attack_hitbox(salve=2)
                if self._hits_player(attack_area, player) and player.health > 0:
                    player.damage(self.damage_amount)
                    self.health = min(self.max_health, self.health + (self.damage_amount * 0.5))
                self.has_dealt_damage_2 = True
        else:
            if player.health > 0 and self.has_aggro:
                if player.feet.centerx > self.feet.centerx: self.facing = "right"
                else: self.facing = "left"

                attack_area = self.get_attack_hitbox()
                
                if current_time - self.last_skill_time > self.skill_cooldown:
                    self.state = 'skill'
                    self.frame_index = 0
                    self.last_skill_time = current_time
                    self.has_summoned = False
                    self.velocity.xy = 0, 0
                elif attack_area.colliderect(player.feet.inflate(8, 8)):
                    if current_time - self.last_attack_time > self.attack_cooldown:
                        self.is_attacking = True
                        self.state = 'attack'
                        self.frame_index = 0
                        self.last_attack_time = current_time
                        self.has_dealt_damage_1 = False
                        self.has_dealt_damage_2 = False
                        self.velocity.xy = 0, 0
                    else:
                        self.state = 'idle'
                        self.velocity.xy = 0, 0
                elif distance > 0:
                    self.state = 'run'
                    norm_dir = target_vector.normalize()
                    self.velocity.x = norm_dir.x * self.speed
                    self.velocity.y = norm_dir.y * self.speed
                else:
                    self.state = 'idle'
                    self.velocity.xy = 0, 0
            else:
                self.state = 'idle'
                self.velocity.xy = 0, 0

        if self.state == 'run':
            self.position.x += self.velocity.x
            self.feet.centerx = round(self.position.x)
            for wall in walls:
                if self.feet.colliderect(wall):
                    if self.velocity.x > 0: self.feet.right = wall.left
                    elif self.velocity.x < 0: self.feet.left = wall.right
                    self.position.x = self.feet.centerx
                    hit_x = True
                    break

            self.position.y += self.velocity.y
            self.feet.bottom = round(self.position.y)
            for wall in walls:
                if self.feet.colliderect(wall):
                    if self.velocity.y > 0: self.feet.bottom = wall.top
                    elif self.velocity.y < 0: self.feet.top = wall.bottom
                    self.position.y = self.feet.bottom
                    hit_y = True
                    break

            if hit_x and abs(norm_dir.y) < 0.5:
                self.position.y += self.speed * self.slide_dir_y
                self.feet.bottom = round(self.position.y)
                for wall in walls:
                    if self.feet.colliderect(wall):
                        self.position.y -= self.speed * self.slide_dir_y
                        self.slide_dir_y *= -1
                        self.position.y += self.speed * self.slide_dir_y
                        self.feet.bottom = round(self.position.y)
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
                        break
                self.feet.centerx = round(self.position.x)

        self.rect.centerx = self.feet.centerx 
        self.rect.bottom = self.feet.bottom + self.y_offset

        self.animate()

    def get_attack_hitbox(self, salve=1):
        # Ancrage sur feet.centerx : la zone part du centre du boss
        # et s'étend uniquement devant lui (dans la direction du regard).
        # Salve 2 : légèrement plus large pour le second balayage ample.
        width = 95 if salve == 1 else 115
        height = 80
        attack_rect = pygame.Rect(0, 0, width, height)

        if self.facing == 'right':
            attack_rect.left = self.feet.centerx - 5
        else:
            attack_rect.right = self.feet.centerx + 5

        # Centré verticalement sur les pieds pour toucher peu importe
        # si le joueur est légèrement au-dessus ou en-dessous du boss.
        attack_rect.centery = self.feet.centery
        return attack_rect

    def _hits_player(self, attack_area, player):
        """Touche si les pieds du joueur (légèrement agrandis) intersectent la zone."""
        # On gonfle un peu les pieds du joueur pour compenser la petite hitbox (15×15).
        # Évite les "faux miss" quand le joueur est visuellement touché mais à 1px du bord.
        return attack_area.colliderect(player.feet.inflate(8, 8))

    def animate(self):
        animation = self.animations[self.facing][self.state]
        speed = self.animation_speed
        if self.state == 'death': speed = 0.1
        
        self.frame_index += speed
        if self.frame_index >= len(animation):
            if self.state == 'death':
                self.frame_index = len(animation) - 1
                self._is_blinking = False
            elif self.state == 'attack' or self.state == 'skill':
                self.is_attacking = False
                self.state = 'idle'
                self.frame_index = 0
            else:
                self.frame_index = 0

        animation = self.animations[self.facing][self.state]
        self.image = animation[int(self.frame_index)].copy()

        if self.state == 'death': self._is_blinking = False
        
        if self._is_blinking:
            if pygame.time.get_ticks() - self.hit_time < 150: 
                mask = pygame.mask.from_surface(self.image)
                red_overlay = mask.to_surface(setcolor=(255, 0, 0, 150), unsetcolor=(0, 0, 0, 0))
                self.image.blit(red_overlay, (0, 0))
            else:
                self._is_blinking = False
            
    def update_volumes(self, music_vol, sfx_vol):
        # Sons gérés via pending_sounds → SpatialAudioManager, rien à ajuster ici
        pygame.mixer.music.set_volume(music_vol)


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
            'scale': 2.5,
            'empty_below': 12 * 2.5,
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
                ('idle',   "assets/images/necromancer_idle.png",       5,  'grid', 5, 1),
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
                ('explode',"assets/images/explosion_anim.png",          5, 'grid', 5, 1),
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

    def _load_strip(self, state_name, path, num_frames):
        try:
            sheet = pygame.image.load(path).convert_alpha()
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
            sheet = pygame.image.load(path).convert_alpha()
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
            sheet = pygame.image.load(path).convert_alpha()
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

    def update(self):
        pass