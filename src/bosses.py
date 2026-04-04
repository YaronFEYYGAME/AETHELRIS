import pygame
import random
import math
from resource_manager import ResourceManager

# On importe les bases depuis tes autres fichiers
from enemy import Enemy
from projectile import Projectile, HomingProjectile, InstantAOE # Ajuste selon ce que tes boss tirent
from item import Item
from utils import draw_pixel_text # Si tes boss affichent des textes ou des barres de vie custom

# ==========================================
# BOSS 1 : BIG ENEMY
# ==========================================

class BigEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.scale_factor = 3.5
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
        self.speed = 1.8
        self.damage_amount = 7.5 
        
        self.aggro_radius = 300 
        
        self.velocity = pygame.math.Vector2(0, 0)
        self.facing = "right"
        
        self.is_attacking = False
        self.last_attack_time = 0
        self.attack_cooldown = 1500
        self._is_blinking = False
        self.hit_time = 0

        self.slide_dir_x = 1
        self.slide_dir_y = 1
        
        self.has_dealt_damage_1 = False
        self.has_dealt_damage_2 = False
        self.has_aggro = False
        self.pending_drop = None

        # Système de dialogue de boss (générique)
        self.dialogue_lines = [
            ("Des visiteurs... ?", 2000),
            ("Votre chemin s'arrête ici.", 2500),
            ("Vous disparaîtrez avec les secrets que renferme ce temple.", 4000),
        ]
        self.dialogue_zone = int(self.aggro_radius * 0.40)
        self.in_dialogue = False
        self.dialogue_finished = False
        self.dialogue_index = 0
        self.dialogue_start_time = 0
        self.invulnerable = False
        self.boss_display_name = "Gardien du Temple"

        # Paralysie
        self.paralyzed = False
        self.paralyze_end_time = 0
        self._blue_cache = {}
        self._gold_cache = {}
        self._zhonya_gold = False

        # Sons gérés via pending_sounds → SpatialAudioManager dans game.py
        self.activation_played = False
        self.death_sound_played = False
        self.bgm_playing = False
        self.pending_sounds = []

    def load_animation(self, state_name, path, num_frames):
        try:
            sprite_sheet = ResourceManager.get_image(path)
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
        if self.in_dialogue or self.invulnerable:
            return
        if self.health > 0 and self.state != 'death':
            self.health -= amount
            self._is_blinking = True
            self.hit_time = pygame.time.get_ticks()

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

    def get_current_dialogue(self):
        """Retourne le texte de la ligne de dialogue en cours, ou None."""
        if self.in_dialogue and self.dialogue_index < len(self.dialogue_lines):
            return self.dialogue_lines[self.dialogue_index][0]
        return None

    def skip_dialogue(self):
        """Skip la ligne de dialogue actuelle. Retourne True si un skip a eu lieu."""
        if not self.in_dialogue:
            return False
        self.dialogue_index += 1
        self.dialogue_start_time = pygame.time.get_ticks()
        if self.dialogue_index >= len(self.dialogue_lines):
            self.in_dialogue = False
            self.dialogue_finished = True
            self.invulnerable = False
            self.has_aggro = True
            if not self.activation_played:
                self.activation_played = True
                self.pending_sounds.append('boss_activation')
            if not self.bgm_playing:
                self.bgm_playing = True
                self.pending_sounds.append('boss_bgm_start')
        return True

    def paralyze(self, duration_ms):
        """Paralyse le boss pour une durée donnée (en ms). Ignoré pendant les dialogues."""
        if self.in_dialogue or not self.dialogue_finished:
            return
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

    def _get_red_tinted(self, frame):
        """Retourne une version teintée en rouge du frame, mise en cache."""
        frame_id = id(frame)
        if not hasattr(self, '_red_cache'):
            self._red_cache = {}
        if frame_id in self._red_cache:
            return self._red_cache[frame_id]
        tinted = frame.copy()
        mask = pygame.mask.from_surface(tinted)
        red_overlay = mask.to_surface(setcolor=(255, 0, 0, 150), unsetcolor=(0, 0, 0, 0))
        tinted.blit(red_overlay, (0, 0))
        self._red_cache[frame_id] = tinted
        return tinted

    def update(self, player, walls):
        if self.state == 'death':
            self.animate()
            return

        # Paralysie : figé, pas de mouvement ni d'attaque
        if self.paralyzed:
            if pygame.time.get_ticks() >= self.paralyze_end_time:
                self.paralyzed = False
                self._zhonya_gold = False
            else:
                self.velocity.xy = 0, 0
                self.animate()
                return

        current_time = pygame.time.get_ticks()

        target_center = pygame.math.Vector2(player.feet.center)
        my_center = pygame.math.Vector2(self.feet.center)
        target_vector = target_center - my_center
        distance = target_vector.length()

        # --- Système de dialogue avant le combat ---
        if not self.dialogue_finished and self.dialogue_lines:
            if not self.in_dialogue:
                if distance < self.dialogue_zone and player.health > 0:
                    self.in_dialogue = True
                    self.invulnerable = True
                    self.dialogue_index = 0
                    self.dialogue_start_time = current_time
            if self.in_dialogue:
                self.velocity.xy = 0, 0
                self.state = 'idle'
                if player.feet.centerx > self.feet.centerx:
                    self.facing = 'right'
                else:
                    self.facing = 'left'
                _, duration = self.dialogue_lines[self.dialogue_index]
                if current_time - self.dialogue_start_time >= duration:
                    self.dialogue_index += 1
                    self.dialogue_start_time = current_time
                    if self.dialogue_index >= len(self.dialogue_lines):
                        self.in_dialogue = False
                        self.dialogue_finished = True
                        self.invulnerable = False
                        self.has_aggro = True
                        self.activation_played = True
                        self.bgm_playing = True
                        self.pending_sounds.append('boss_activation')
                        self.pending_sounds.append('boss_bgm_start')
                self.animate()
                return

        # --- Aggro classique (uniquement après fin des dialogues) ---
        if self.dialogue_lines and not self.dialogue_finished:
            self.animate()
            return

        if distance < self.aggro_radius and player.health > 0:
            if not self.has_aggro:
                self.has_aggro = True
                if not self.dialogue_lines or self.dialogue_finished:
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

        hit_x = False
        hit_y = False
        norm_dir = pygame.math.Vector2(0, 0)

        if self.is_attacking:
            self.velocity.xy = 0, 0 
            current_frame = int(self.frame_index)
            
            if current_frame == 1 and not self.has_dealt_damage_1:
                attack_area = self.get_attack_hitbox()
                if attack_area.colliderect(player.feet.inflate(20, 20)) and player.health > 0:
                    hp_before = player.health
                    player.damage(self.damage_amount, source_enemy=self)
                    if player.health < hp_before:
                        self.health = min(self.max_health, self.health + (self.damage_amount * 0.3))
                self.has_dealt_damage_1 = True

            elif current_frame == 5 and not self.has_dealt_damage_2:
                self.pending_sounds.append('boss_attack')

                attack_area = self.get_attack_hitbox()
                if attack_area.colliderect(player.feet.inflate(20, 20)) and player.health > 0:
                    hp_before = player.health
                    player.damage(self.damage_amount, source_enemy=self)
                    if player.health < hp_before:
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
        range_attack = 189
        width_attack = 8

        attack_rect = pygame.Rect(0, 0, range_attack, width_attack)

        if self.facing == 'right':
            attack_rect.left = self.feet.left - 14
        else:
            attack_rect.right = self.feet.right + 14

        attack_rect.bottom = self.feet.centery + 21
        return attack_rect

    def animate(self):
        animation = self.animations[self.facing][self.state]

        # Paralysie : frame figée + teinte (rouge prioritaire si blessure récente)
        if self.paralyzed:
            idx = max(0, min(int(self.frame_index), len(animation) - 1))
            base = animation[idx]
            if self._is_blinking and pygame.time.get_ticks() - self.hit_time < 150:
                self.image = self._get_red_tinted(base)
            else:
                if pygame.time.get_ticks() - self.hit_time >= 150:
                    self._is_blinking = False
                if self._zhonya_gold:
                    self.image = self._get_gold_tinted(base)
                else:
                    self.image = self._get_blue_tinted(base)
            return

        speed = self.animation_speed
        if self.state == 'death': speed = 0.1

        self.frame_index += speed

        if self.frame_index >= len(animation):
            if self.state == 'death':
                self.frame_index = len(animation) - 1
                self._is_blinking = False
            elif self.state == 'attack':
                self.is_attacking = False
                self.state = 'idle'
                self.frame_index = 0
            else:
                self.frame_index = 0

        animation = self.animations[self.facing][self.state]
        base_frame = animation[int(self.frame_index)]

        if self.state == 'death':
            self._is_blinking = False

        if self._is_blinking:
            if pygame.time.get_ticks() - self.hit_time < 150:
                self.image = self._get_red_tinted(base_frame)
            else:
                self._is_blinking = False
                self.image = base_frame.copy()
        else:
            self.image = base_frame.copy()

    def update_volumes(self, music_vol, sfx_vol):
        # Sons gérés via pending_sounds → SpatialAudioManager, rien à ajuster ici
        pygame.mixer.music.set_volume(music_vol)


# ==========================================
# BOSS 2 : NECROMANCER
# ==========================================

class Spirit(pygame.sprite.Sprite):
    """Summon du Necromancer. Suit le joueur le plus proche et explose à son contact."""
    def __init__(self, x, y, owner_necromancer=None):
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

        self.max_health = 1
        self.health = 1
        self.speed = 1.8
        self.velocity = pygame.math.Vector2(0, 0)
        self.facing = "right"
        self.damage_amount = 15
        self.is_dead = False

        # Référence au Necromancer propriétaire (pour le lifesteal)
        self.owner = owner_necromancer
        # Flag pour spawner des particules rouges à la mort/explosion
        self.pending_particles = False

        # Paralysie
        self.paralyzed = False
        self.paralyze_end_time = 0
        self._blue_cache = {}
        self._gold_cache = {}
        self._zhonya_gold = False

    def paralyze(self, duration_ms):
        self.paralyzed = True
        self.paralyze_end_time = pygame.time.get_ticks() + duration_ms

    def _get_blue_tinted(self, frame):
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

    def load_grid_animation(self, state_name, path, cols, rows, num_frames, scale_override=None):
        scale = scale_override if scale_override is not None else self.scale_factor
        try:
            sprite_sheet = ResourceManager.get_image(path)
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
            print(f"Erreur: Fichier {path} introuvable.")

    def damage(self, amount):
        if self.health > 0 and self.state != 'death':
            self.health -= amount
            if self.health <= 0:
                self.health = 0
                self.is_dead = True
                self.pending_particles = True
                self.kill()

    def update(self, player, walls):
        if self.state == 'death':
            self.animate()
            if self.frame_index >= len(self.animations[self.facing]['death']) - 1:
                self.kill()
            return

        if self.state == 'appear':
            self.animate()
            if self.frame_index >= len(self.animations[self.facing]['appear']) - 1:
                self.state = 'run'
                self.frame_index = 0
            return

        # Paralysie : figé
        if self.paralyzed:
            if pygame.time.get_ticks() >= self.paralyze_end_time:
                self.paralyzed = False
                self._zhonya_gold = False
            else:
                self.velocity.xy = 0, 0
                self.animate()
                return

        target_center = pygame.math.Vector2(player.feet.center)
        my_center = pygame.math.Vector2(self.feet.center)
        target_vector = target_center - my_center
        distance = target_vector.length()

        if distance < 25 and player.health > 0:
            hp_before = player.health
            player.damage(self.damage_amount, source_enemy=self)
            actual_damage = hp_before - player.health
            if actual_damage > 0:
                # Lifesteal du Necromancer : 100% des dégâts infligés
                if self.owner and hasattr(self.owner, 'health') and self.owner.health > 0:
                    self.owner.health = min(self.owner.max_health, self.owner.health + actual_damage)
            # Disparaît avec particules rouges (pas d'animation d'explosion)
            self.pending_particles = True
            self.kill()
            return
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

        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom + self.y_offset

        self.animate()

    def animate(self):
        animation = self.animations[self.facing][self.state]

        # Paralysie : frame figée + teinte bleue
        if self.paralyzed:
            idx = max(0, min(int(self.frame_index), len(animation) - 1))
            if self._zhonya_gold:
                self.image = self._get_gold_tinted(animation[idx])
            else:
                self.image = self._get_blue_tinted(animation[idx])
            self.rect.centerx = self.feet.centerx
            self.rect.bottom = self.feet.bottom + self.y_offset
            return

        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            if self.state in ['death', 'appear']:
                self.frame_index = len(animation) - 1
            else:
                self.frame_index = 0
        frame_idx = max(0, min(int(self.frame_index), len(animation) - 1))
        self.image = animation[frame_idx]

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

        self.load_grid_animation('idle', "assets/images/necromancer_idle.png", 5, 1, 4)  # 5e frame vide
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
        self.speed = 1.8
        self.damage_amount = 10
        self.aggro_radius = 400

        self.velocity = pygame.math.Vector2(0, 0)
        self.facing = "right"
        self.is_attacking = False
        self.last_attack_time = 0
        self.attack_cooldown = 1800

        # Invocation de summons
        self.last_skill_time = 0
        self.skill_cooldown = 16000  # 16 secondes entre chaque invocation
        self.has_summoned = False
        self.pending_summons = []
        self.pending_drop = None

        self._is_blinking = False
        self.hit_time = 0
        self.has_dealt_damage_1 = False
        self.has_dealt_damage_2 = False
        self.has_aggro = False

        self.slide_dir_x = 1
        self.slide_dir_y = 1
        self.pending_sounds = []

        # Système de dialogue de boss (comme BigEnemy)
        self.dialogue_lines = [
            ("Enfin de nouvelles \u00e2mes...", 2500),
            ("Je vais me faire un plaisir de vous \u00e9ventrer.", 4000),
        ]
        self.dialogue_zone = int(self.aggro_radius * 0.40)
        self.in_dialogue = False
        self.dialogue_finished = False
        self.dialogue_index = 0
        self.dialogue_start_time = 0
        self.invulnerable = False
        self.boss_display_name = "Nécromancien"

        # Sons & musique
        self.activation_played = False
        self.death_sound_played = False
        self.bgm_playing = False

        # Paralysie
        self.paralyzed = False
        self.paralyze_end_time = 0
        self._blue_cache = {}
        self._gold_cache = {}
        self._zhonya_gold = False

    def paralyze(self, duration_ms):
        if self.in_dialogue or not self.dialogue_finished:
            return
        self.paralyzed = True
        self.paralyze_end_time = pygame.time.get_ticks() + duration_ms

    def _get_blue_tinted(self, frame):
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

    def load_grid_animation(self, state_name, path, cols, rows, num_frames):
        try:
            sprite_sheet = ResourceManager.get_image(path)
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
            print(f"Erreur: Fichier {path} introuvable.")

    def get_current_dialogue(self):
        """Retourne le texte de la ligne de dialogue en cours, ou None."""
        if self.in_dialogue and self.dialogue_index < len(self.dialogue_lines):
            return self.dialogue_lines[self.dialogue_index][0]
        return None

    def skip_dialogue(self):
        """Skip la ligne de dialogue actuelle. Retourne True si un skip a eu lieu."""
        if not self.in_dialogue:
            return False
        self.dialogue_index += 1
        self.dialogue_start_time = pygame.time.get_ticks()
        if self.dialogue_index >= len(self.dialogue_lines):
            self.in_dialogue = False
            self.dialogue_finished = True
            self.invulnerable = False
            self.has_aggro = True
            if not self.activation_played:
                self.activation_played = True
                self.pending_sounds.append('necro_activation')
            if not self.bgm_playing:
                self.bgm_playing = True
                self.pending_sounds.append('necro_bgm_start')
        return True

    def damage(self, amount):
        if self.in_dialogue or self.invulnerable:
            return
        if self.health > 0 and self.state != 'death':
            self.health -= amount
            self._is_blinking = True
            self.hit_time = pygame.time.get_ticks()

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

    def update(self, player, walls):
        if self.state == 'death':
            self.animate()
            return

        # Paralysie : figé
        if self.paralyzed:
            if pygame.time.get_ticks() >= self.paralyze_end_time:
                self.paralyzed = False
                self._zhonya_gold = False
            else:
                self.velocity.xy = 0, 0
                self.animate()
                return

        current_time = pygame.time.get_ticks()
        target_center = pygame.math.Vector2(player.feet.center)
        my_center = pygame.math.Vector2(self.feet.center)
        target_vector = target_center - my_center
        distance = target_vector.length()

        # --- Système de dialogue avant le combat ---
        if not self.dialogue_finished and self.dialogue_lines:
            if not self.in_dialogue:
                if distance < self.dialogue_zone and player.health > 0:
                    self.in_dialogue = True
                    self.invulnerable = True
                    self.dialogue_index = 0
                    self.dialogue_start_time = current_time
            if self.in_dialogue:
                self.velocity.xy = 0, 0
                self.state = 'idle'
                if player.feet.centerx > self.feet.centerx:
                    self.facing = 'right'
                else:
                    self.facing = 'left'
                _, duration = self.dialogue_lines[self.dialogue_index]
                if current_time - self.dialogue_start_time >= duration:
                    self.dialogue_index += 1
                    self.dialogue_start_time = current_time
                    if self.dialogue_index >= len(self.dialogue_lines):
                        self.in_dialogue = False
                        self.dialogue_finished = True
                        self.invulnerable = False
                        self.has_aggro = True
                        self.activation_played = True
                        self.bgm_playing = True
                        self.pending_sounds.append('boss_activation')
                        self.pending_sounds.append('necro_bgm_start')
                        # Premier summon juste après le dialogue
                        self.last_skill_time = current_time - self.skill_cooldown
                self.animate()
                return

        # --- Aggro classique (uniquement après fin des dialogues) ---
        if self.dialogue_lines and not self.dialogue_finished:
            self.animate()
            return

        if distance < self.aggro_radius and player.health > 0:
            if not self.has_aggro:
                self.has_aggro = True
                if not self.dialogue_lines or self.dialogue_finished:
                    if not self.activation_played:
                        self.activation_played = True
                        self.pending_sounds.append('boss_activation')
                    if not self.bgm_playing:
                        self.bgm_playing = True
                        self.pending_sounds.append('necro_bgm_start')
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
                self._spawn_summons()
                self.has_summoned = True

        elif self.is_attacking:
            self.velocity.xy = 0, 0
            current_frame = int(self.frame_index)
            if current_frame == 3 and not self.has_dealt_damage_1:
                self.pending_sounds.append('boss_attack')
                attack_area = self.get_attack_hitbox(salve=1)
                if self._hits_player(attack_area, player) and player.health > 0:
                    hp_before = player.health
                    player.damage(self.damage_amount, source_enemy=self)
                    if player.health < hp_before:
                        self.health = min(self.max_health, self.health + (self.damage_amount * 0.5))
                self.has_dealt_damage_1 = True
            elif current_frame == 8 and not self.has_dealt_damage_2:
                self.pending_sounds.append('boss_attack')
                attack_area = self.get_attack_hitbox(salve=2)
                if self._hits_player(attack_area, player) and player.health > 0:
                    hp_before = player.health
                    player.damage(self.damage_amount, source_enemy=self)
                    if player.health < hp_before:
                        self.health = min(self.max_health, self.health + (self.damage_amount * 0.5))
                self.has_dealt_damage_2 = True
        else:
            if player.health > 0 and self.has_aggro:
                if player.feet.centerx > self.feet.centerx: self.facing = "right"
                else: self.facing = "left"

                # Invocation de summons (cooldown)
                if current_time - self.last_skill_time > self.skill_cooldown:
                    self.state = 'skill'
                    self.frame_index = 0
                    self.last_skill_time = current_time
                    self.has_summoned = False
                    self.velocity.xy = 0, 0
                elif self.get_attack_hitbox().colliderect(player.feet.inflate(8, 8)):
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

    def _spawn_summons(self):
        """Ajoute 3 summons autour de la position actuelle du Necromancer."""
        cx, cy = self.feet.centerx, self.feet.bottom
        self.pending_summons.append((cx - 60, cy + 20))
        self.pending_summons.append((cx + 60, cy + 20))
        self.pending_summons.append((cx, cy - 50))

    def get_attack_hitbox(self, salve=1):
        width = 55 if salve == 1 else 65
        height = 40
        attack_rect = pygame.Rect(0, 0, width, height)

        if self.facing == 'right':
            attack_rect.left = self.feet.centerx
        else:
            attack_rect.right = self.feet.centerx

        attack_rect.centery = self.feet.centery
        return attack_rect

    def _hits_player(self, attack_area, player):
        return attack_area.colliderect(player.feet.inflate(8, 8))

    def animate(self):
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

        # Re-fetch animation au cas où l'état a changé, puis clamp l'index
        animation = self.animations[self.facing][self.state]
        frame_idx = max(0, min(int(self.frame_index), len(animation) - 1))
        self.image = animation[frame_idx]

        if self.state == 'death': self._is_blinking = False

        if self._is_blinking:
            if pygame.time.get_ticks() - self.hit_time < 150:
                self.image = self.image.copy()
                mask = pygame.mask.from_surface(self.image)
                red_overlay = mask.to_surface(setcolor=(255, 0, 0, 150), unsetcolor=(0, 0, 0, 0))
                self.image.blit(red_overlay, (0, 0))
            else:
                self._is_blinking = False

    def update_volumes(self, music_vol, sfx_vol):
        pygame.mixer.music.set_volume(music_vol)



# ==========================================
# BOSS 3 : MEDUSA
# ==========================================

class Medusa(pygame.sprite.Sprite):
    """Boss Médusa. Deux attaques de base + ultime avec stun et vol de vie."""

    SPRITE_DIR = "assets/images/Medusa_boss/"
    RUN_DISTANCE_THRESHOLD = 120  # distance au-delà de laquelle elle court

    def __init__(self, x, y):
        super().__init__()
        self.scale_factor = 1.0
        self.animations = {'right': {}, 'left': {}}
        self.state = 'idle'
        self.frame_index = 0
        self.animation_speed = 0.15

        # Charger toutes les animations (spritesheets horizontales)
        self.load_animation('idle',    self.SPRITE_DIR + "Idle.png",     7)
        self.load_animation('walk',    self.SPRITE_DIR + "Walk.png",     13)
        self.load_animation('run',     self.SPRITE_DIR + "Run.png",      7)
        self.load_animation('attack1', self.SPRITE_DIR + "Attack_1.png", 16)
        self.load_animation('attack2', self.SPRITE_DIR + "Attack_2.png", 7)
        self.load_animation('special', self.SPRITE_DIR + "Special.png",  5)
        self.load_animation('hurt',    self.SPRITE_DIR + "Hurt.png",     3)
        self.load_animation('death',   self.SPRITE_DIR + "Dead.png",     3)

        self.image = self.animations['right']['idle'][0]
        self.rect = self.image.get_rect()

        hitbox_width = 16
        hitbox_height = 30
        self.feet = pygame.Rect(0, 0, hitbox_width, hitbox_height)

        self.y_offset = 8

        self.position = pygame.math.Vector2(x, y)
        self.feet.midbottom = (round(self.position.x), round(self.position.y))

        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom + self.y_offset

        # Stats (1.5x BigEnemy HP)
        self.max_health = 585
        self.health = 585
        self.base_speed = 1.5
        self.speed = self.base_speed
        self.damage_amount = 7.5
        self.special_damage = 10

        self.aggro_radius = 300

        self.velocity = pygame.math.Vector2(0, 0)
        self.facing = "right"

        self.is_attacking = False
        self.last_attack_time = 0
        self.attack_cooldown = 1100
        self._is_blinking = False
        self.hit_time = 0

        # Tracking de dégâts par frame d'attaque
        self.has_dealt_damage = False

        self.has_aggro = False
        self.pending_drop = None

        self.slide_dir_x = 1
        self.slide_dir_y = 1

        # Course : quand le joueur est trop loin
        self.is_running = False

        # Dialogue de boss
        self.dialogue_lines = [
            ("Ssssss... des intrus....", 2000),
            ("Cela faisait longtemps que personne n'était venu s'aventurer ici Ssssss....", 4000),
            ("Ssssss.... Vous feriez de belles statues dans ma collection Sssss...", 4000),
            ("EN GARDE SSSSSSSS....", 2000),
        ]
        self.dialogue_zone = int(self.aggro_radius * 0.40)
        self.in_dialogue = False
        self.dialogue_finished = False
        self.dialogue_index = 0
        self.dialogue_start_time = 0
        self.invulnerable = False
        self.boss_display_name = "Médusa"

        # Sons
        self.activation_played = False
        self.death_sound_played = False
        self.bgm_playing = False
        self.pending_sounds = []

        # Paralysie
        self.paralyzed = False
        self.paralyze_end_time = 0
        self._blue_cache = {}
        self._gold_cache = {}
        self._zhonya_gold = False

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
            print(f"Erreur: Fichier {path} introuvable.")

    def paralyze(self, duration_ms):
        if self.in_dialogue or not self.dialogue_finished:
            return
        self.paralyzed = True
        self.paralyze_end_time = pygame.time.get_ticks() + duration_ms

    def _get_blue_tinted(self, frame):
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
        if self.in_dialogue or self.invulnerable:
            return
        if self.health > 0 and self.state != 'death':
            self.health -= amount
            self._is_blinking = True
            self.hit_time = pygame.time.get_ticks()

            if self.health <= 0:
                self.health = 0
                self.state = 'death'
                self.frame_index = 0
                self.is_attacking = False
                self.velocity.xy = 0, 0
                self._is_blinking = False
                if not self.death_sound_played:
                    self.death_sound_played = True
                    self.pending_sounds.append('medusa_death')
                if self.bgm_playing:
                    self.bgm_playing = False
                    self.pending_sounds.append('boss_bgm_stop')

    def get_current_dialogue(self):
        if self.in_dialogue and self.dialogue_index < len(self.dialogue_lines):
            return self.dialogue_lines[self.dialogue_index][0]
        return None

    def skip_dialogue(self):
        """Skip la ligne de dialogue actuelle. Retourne True si un skip a eu lieu."""
        if not self.in_dialogue:
            return False
        self.dialogue_index += 1
        self.dialogue_start_time = pygame.time.get_ticks()
        if self.dialogue_index >= len(self.dialogue_lines):
            self.in_dialogue = False
            self.dialogue_finished = True
            self.invulnerable = False
            self.has_aggro = True
            if not self.activation_played:
                self.activation_played = True
            if not self.bgm_playing:
                self.bgm_playing = True
                self.pending_sounds.append('medusa_bgm_start')
        return True

    def get_attack_hitbox(self, attack_type=None):
        """Hitbox adaptée au type d'attaque. Si None, utilise l'état courant."""
        if attack_type is None:
            attack_type = self.state if self.state in ('attack1', 'attack2', 'special') else 'attack1'
        if attack_type == 'attack1':
            width = 30
            height = 25
        elif attack_type == 'attack2':
            width = 55
            height = 35
        else:
            # Special : grande zone devant Médusa
            width = 100
            height = 60

        attack_rect = pygame.Rect(0, 0, width, height)
        if self.facing == 'right':
            attack_rect.left = self.feet.left
        else:
            attack_rect.right = self.feet.right
        attack_rect.centery = self.feet.centery
        return attack_rect

    def _choose_attack(self):
        """Choisit une attaque : 1/6 chance ultime, sinon 50/50 entre attack1 et attack2."""
        import random
        roll = random.randint(1, 6)
        if roll == 1:
            return 'special'
        elif random.random() < 0.5:
            return 'attack1'
        else:
            return 'attack2'

    def update(self, player, walls):
        if self.state == 'death':
            self.animate()
            return

        # Paralysie
        if self.paralyzed:
            if pygame.time.get_ticks() >= self.paralyze_end_time:
                self.paralyzed = False
                self._zhonya_gold = False
            else:
                self.velocity.xy = 0, 0
                self.animate()
                return

        current_time = pygame.time.get_ticks()
        target_center = pygame.math.Vector2(player.feet.center)
        my_center = pygame.math.Vector2(self.feet.center)
        target_vector = target_center - my_center
        distance = target_vector.length()

        # --- Dialogue avant le combat ---
        if not self.dialogue_finished and self.dialogue_lines:
            if not self.in_dialogue:
                if distance < self.dialogue_zone and player.health > 0:
                    self.in_dialogue = True
                    self.invulnerable = True
                    self.dialogue_index = 0
                    self.dialogue_start_time = current_time
            if self.in_dialogue:
                self.velocity.xy = 0, 0
                self.state = 'idle'
                if player.feet.centerx > self.feet.centerx:
                    self.facing = 'right'
                else:
                    self.facing = 'left'
                _, duration = self.dialogue_lines[self.dialogue_index]
                if current_time - self.dialogue_start_time >= duration:
                    self.dialogue_index += 1
                    self.dialogue_start_time = current_time
                    if self.dialogue_index >= len(self.dialogue_lines):
                        self.in_dialogue = False
                        self.dialogue_finished = True
                        self.invulnerable = False
                        self.has_aggro = True
                        self.activation_played = True
                        self.bgm_playing = True
                        self.pending_sounds.append('medusa_bgm_start')
                self.animate()
                return

        if self.dialogue_lines and not self.dialogue_finished:
            self.animate()
            return

        # --- Aggro ---
        if distance < self.aggro_radius and player.health > 0:
            if not self.has_aggro:
                self.has_aggro = True
                if not self.activation_played:
                    self.activation_played = True
                if not self.bgm_playing:
                    self.bgm_playing = True
                    self.pending_sounds.append('medusa_bgm_start')
        elif player.health <= 0:
            self.has_aggro = False
            if self.bgm_playing:
                self.bgm_playing = False
                self.pending_sounds.append('boss_bgm_stop')

        hit_x = False
        hit_y = False
        norm_dir = pygame.math.Vector2(0, 0)

        if self.is_attacking:
            self.velocity.xy = 0, 0
            current_frame = int(self.frame_index)
            attack_state = self.state

            # Dégâts à mi-animation
            if not self.has_dealt_damage:
                damage_frame = self._get_damage_frame(attack_state)
                if current_frame >= damage_frame:
                    self.has_dealt_damage = True
                    hitbox = self.get_attack_hitbox(attack_state)
                    if hitbox.colliderect(player.feet.inflate(20, 20)) and player.health > 0:
                        if attack_state == 'special':
                            # Ultime : stun + vol de vie (seulement si les dégâts passent)
                            self.pending_sounds.append(random.choice(['medusa_ult_1', 'medusa_ult_2']))
                            hp_before = player.health
                            player.damage(self.special_damage, source_enemy=self)
                            if player.health < hp_before:
                                # Dégâts infligés → stun + heal
                                player.apply_stun(2000)
                                missing_hp = self.max_health - self.health
                                heal = missing_hp * 0.5
                                self.health = min(self.max_health, self.health + heal)
                        else:
                            # Attaque normale
                            self.pending_sounds.append(random.choice(['medusa_attack_1', 'medusa_attack_2', 'medusa_attack_3', 'medusa_attack_4']))
                            player.damage(self.damage_amount, source_enemy=self)
        else:
            if player.health > 0 and self.has_aggro:
                if player.feet.centerx > self.feet.centerx:
                    self.facing = 'right'
                else:
                    self.facing = 'left'

                attack_hitbox = self.get_attack_hitbox()
                at_melee_range = attack_hitbox.colliderect(player.feet.inflate(20, 20))

                if at_melee_range:
                    if self.is_running:
                        # Arrivée après une course → ultime immédiat (ignore le cooldown)
                        self.is_running = False
                        self.speed = self.base_speed
                        self.is_attacking = True
                        self.state = 'special'
                        self.frame_index = 0
                        self.last_attack_time = current_time
                        self.has_dealt_damage = False
                        self.velocity.xy = 0, 0
                        self.pending_sounds.append(random.choice(['medusa_ult_1', 'medusa_ult_2']))
                    elif current_time - self.last_attack_time > self.attack_cooldown:
                        chosen = self._choose_attack()
                        self.is_attacking = True
                        self.state = chosen
                        self.frame_index = 0
                        self.last_attack_time = current_time
                        self.has_dealt_damage = False
                        self.velocity.xy = 0, 0
                        self.pending_sounds.append(random.choice(['medusa_attack_1', 'medusa_attack_2', 'medusa_attack_3', 'medusa_attack_4']))
                    else:
                        self.state = 'idle'
                        self.velocity.xy = 0, 0
                elif distance < self.aggro_radius and distance > 0:
                    # Déplacement vers le joueur
                    if self.is_running:
                        # En course : ne PAS s'arrêter avant le corps à corps
                        self.state = 'run'
                        self.speed = self.base_speed * 2
                    elif distance > self.RUN_DISTANCE_THRESHOLD:
                        # Trop loin → commencer la course (vitesse x2)
                        self.is_running = True
                        self.speed = self.base_speed * 2
                        self.state = 'run'
                    else:
                        # Proche → marche normale
                        self.state = 'walk'
                        self.speed = self.base_speed
                    norm_dir = target_vector.normalize()
                    self.velocity.x = norm_dir.x * self.speed
                    self.velocity.y = norm_dir.y * self.speed
                else:
                    self.state = 'idle'
                    self.velocity.xy = 0, 0
            else:
                self.state = 'idle'
                self.velocity.xy = 0, 0

        # Mouvement
        if self.state in ('walk', 'run'):
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

            # Contournement des murs
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

    def _get_damage_frame(self, attack_state):
        """Frame à laquelle les dégâts sont infligés."""
        if attack_state == 'attack1':
            return 8   # mi-animation des 16 frames
        elif attack_state == 'attack2':
            return 3   # mi-animation des 7 frames
        elif attack_state == 'special':
            return 1   # tôt dans l'animation des 5 frames
        return 0

    def _get_red_tinted(self, frame):
        """Retourne une version teintée en rouge du frame, mise en cache."""
        frame_id = id(frame)
        if not hasattr(self, '_red_cache'):
            self._red_cache = {}
        if frame_id in self._red_cache:
            return self._red_cache[frame_id]
        tinted = frame.copy()
        mask = pygame.mask.from_surface(tinted)
        red_overlay = mask.to_surface(setcolor=(255, 0, 0, 150), unsetcolor=(0, 0, 0, 0))
        tinted.blit(red_overlay, (0, 0))
        self._red_cache[frame_id] = tinted
        return tinted

    def animate(self):
        animation = self.animations[self.facing][self.state]

        # Paralysie : frame figée + teinte bleue (rouge prioritaire si blessure récente)
        if self.paralyzed:
            idx = max(0, min(int(self.frame_index), len(animation) - 1))
            base = animation[idx]
            if self._is_blinking and pygame.time.get_ticks() - self.hit_time < 150:
                self.image = self._get_red_tinted(base)
            else:
                if pygame.time.get_ticks() - self.hit_time >= 150:
                    self._is_blinking = False
                if self._zhonya_gold:
                    self.image = self._get_gold_tinted(base)
                else:
                    self.image = self._get_blue_tinted(base)
            return

        speed = self.animation_speed
        if self.state == 'death':
            speed = 0.1

        self.frame_index += speed

        if self.frame_index >= len(animation):
            if self.state == 'death':
                self.frame_index = len(animation) - 1
                self._is_blinking = False
            elif self.state in ('attack1', 'attack2', 'special'):
                if self.state == 'special':
                    # Enchaînement immédiat après l'ultime
                    self.last_attack_time = pygame.time.get_ticks() - self.attack_cooldown
                self.is_attacking = False
                self.state = 'idle'
                self.frame_index = 0
            else:
                self.frame_index = 0

        animation = self.animations[self.facing][self.state]
        base_frame = animation[int(self.frame_index)]

        if self.state == 'death':
            self._is_blinking = False

        if self._is_blinking:
            if pygame.time.get_ticks() - self.hit_time < 150:
                self.image = self._get_red_tinted(base_frame)
            else:
                self._is_blinking = False
                self.image = base_frame.copy()
        else:
            self.image = base_frame.copy()

    def update_volumes(self, music_vol, sfx_vol):
        pygame.mixer.music.set_volume(music_vol)


# ==========================================
# BOSS 4 : KING BOSS
# ==========================================

class KingBoss(pygame.sprite.Sprite):
    """Boss Roi réprouvé. Attaque à la faux, régénération, stun global."""

    SPRITE_DIR = "assets/images/king_boss/"
    FRAME_W = 128
    FRAME_H = 64

    def __init__(self, x, y):
        super().__init__()
        self.scale_factor = 1.5
        self.animations = {'right': {}, 'left': {}}
        self.state = 'idle'
        self.frame_index = 0
        self.animation_speed = 0.15

        # Charger les animations (grilles de 128×64 par frame)
        self._load_grid_animation('idle',   self.SPRITE_DIR + "Idle.png")
        self._load_grid_animation('run',    self.SPRITE_DIR + "Run.png")
        self._load_grid_animation('death',  self.SPRITE_DIR + "Death.png")
        self._load_grid_animation('health', self.SPRITE_DIR + "Health.png")
        self._load_grid_animation('pray',   self.SPRITE_DIR + "Pray.png")

        # Attaque : 5 rangées de 8 frames — rangée 1 (droite) et rangée 2 (gauche)
        self._load_attack_animation()

        self.image = self.animations['right']['idle'][0]
        self.rect = self.image.get_rect()

        hitbox_width = int(16 * self.scale_factor)
        hitbox_height = int(10 * self.scale_factor)
        self.feet = pygame.Rect(0, 0, hitbox_width, hitbox_height)

        self.y_offset = int(8 * self.scale_factor)

        self.position = pygame.math.Vector2(x, y)
        self.feet.midbottom = (round(self.position.x), round(self.position.y))
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom + self.y_offset

        # Stats
        self.max_health = 1200
        self.health = 1200
        self.speed = 1.8  # même vitesse que BigEnemy
        self.damage_amount = 10

        self.aggro_radius = 300

        self.velocity = pygame.math.Vector2(0, 0)
        self.facing = "right"

        self.is_attacking = False
        self.last_attack_time = 0
        self.attack_cooldown = 1200
        self._is_blinking = False
        self.hit_time = 0

        self.has_dealt_damage = False
        self._damage_frames = {2, 4, 6}  # 3 salves de dégâts
        self._dealt_frames = set()  # frames déjà infligées
        self.has_aggro = False
        self.pending_drop = None

        self.slide_dir_x = 1
        self.slide_dir_y = 1

        # Dialogue de boss
        self.dialogue_lines = [
            ("Vous osez fouler ces terres sacrees...", 4000),
            ("Je suis le gardien de ce royaume dechu.", 4000),
            ("Agenouillez-vous... ou perissez.", 3000),
        ]
        self.dialogue_zone = int(self.aggro_radius * 0.40)
        self.in_dialogue = False
        self.dialogue_finished = False
        self.dialogue_index = 0
        self.dialogue_start_time = 0
        self.invulnerable = False
        self.boss_display_name = "Roi reprouve"

        # Sons
        self.activation_played = False
        self.death_sound_played = False
        self.bgm_playing = False
        self.pending_sounds = []

        # Paralysie
        self.paralyzed = False
        self.paralyze_end_time = 0
        self._blue_cache = {}
        self._gold_cache = {}
        self._red_cache = {}
        self._zhonya_gold = False

        # Compétence 1 : Régénération
        self.regen_cooldown = 30000  # 30 secondes
        self.last_regen_time = -30000
        self.regen_threshold = 0.70  # en dessous de 70% PV max
        self.is_healing = False

        # Compétence 2 : Stun global
        self.stun_cooldown = 20000  # 20 secondes
        self.last_stun_time = -20000
        self.stun_threshold = 0.90  # en dessous de 90% PV max
        self.is_praying = False
        self.pray_stun_applied = False

        # Pending stun (géré par game.py)
        self.pending_global_stun = False

    def _load_grid_animation(self, state_name, path):
        """Charge une spritesheet en grille de FRAME_W × FRAME_H."""
        try:
            sheet = ResourceManager.get_image(path)
            cols = sheet.get_width() // self.FRAME_W
            rows = sheet.get_height() // self.FRAME_H
            frames_right = []
            frames_left = []
            for r in range(rows):
                for c in range(cols):
                    frame = sheet.subsurface((c * self.FRAME_W, r * self.FRAME_H,
                                              self.FRAME_W, self.FRAME_H))
                    nw = int(self.FRAME_W * self.scale_factor)
                    nh = int(self.FRAME_H * self.scale_factor)
                    frame = pygame.transform.scale(frame, (nw, nh))
                    frames_right.append(frame)
                    frames_left.append(pygame.transform.flip(frame, True, False))
            self.animations['right'][state_name] = frames_right
            self.animations['left'][state_name] = frames_left
        except FileNotFoundError:
            print(f"Erreur: Fichier {path} introuvable.")

    def _load_attack_animation(self):
        """Charge l'attaque : rangée 3, même pattern que _load_grid_animation (raw=right, flip=left)."""
        try:
            sheet = ResourceManager.get_image(self.SPRITE_DIR + "Attacks.png")
            nw = int(self.FRAME_W * self.scale_factor)
            nh = int(self.FRAME_H * self.scale_factor)

            # Rangée 3 : attaque horizontale (même orientation que idle/run)
            frames_right = []
            frames_left = []
            for c in range(8):
                frame = sheet.subsurface((c * self.FRAME_W, 3 * self.FRAME_H,
                                          self.FRAME_W, self.FRAME_H))
                frame = pygame.transform.scale(frame, (nw, nh))
                frames_right.append(frame)
                frames_left.append(pygame.transform.flip(frame, True, False))

            self.animations['right']['attack'] = frames_left
            self.animations['left']['attack'] = frames_right
        except FileNotFoundError:
            print("Erreur: Attacks.png introuvable.")

    def damage(self, amount):
        if self.in_dialogue or self.invulnerable:
            return
        if self.health > 0 and self.state != 'death':
            self.health -= amount
            self._is_blinking = True
            self.hit_time = pygame.time.get_ticks()

            if self.health <= 0:
                self.health = 0
                self.state = 'death'
                self.frame_index = 0
                self.is_attacking = False
                self.is_healing = False
                self.is_praying = False
                self.velocity.xy = 0, 0
                self._is_blinking = False
                if not self.death_sound_played:
                    self.death_sound_played = True
                    self.pending_sounds.append('boss_death')
                if self.bgm_playing:
                    self.bgm_playing = False
                    self.pending_sounds.append('boss_bgm_stop')

    def get_current_dialogue(self):
        if self.in_dialogue and self.dialogue_index < len(self.dialogue_lines):
            return self.dialogue_lines[self.dialogue_index][0]
        return None

    def skip_dialogue(self):
        """Skip la ligne de dialogue actuelle."""
        if not self.in_dialogue:
            return False
        self.dialogue_index += 1
        self.dialogue_start_time = pygame.time.get_ticks()
        if self.dialogue_index >= len(self.dialogue_lines):
            self.in_dialogue = False
            self.dialogue_finished = True
            self.invulnerable = False
            self.has_aggro = True
            if not self.activation_played:
                self.activation_played = True
                self.pending_sounds.append('boss_activation')
            if not self.bgm_playing:
                self.bgm_playing = True
                self.pending_sounds.append('king_bgm_start')
        return True

    def paralyze(self, duration_ms):
        if self.in_dialogue or not self.dialogue_finished:
            return
        self.paralyzed = True
        self.paralyze_end_time = pygame.time.get_ticks() + duration_ms

    def _get_blue_tinted(self, frame):
        frame_id = id(frame)
        if frame_id in self._blue_cache:
            return self._blue_cache[frame_id]
        tinted = frame.copy()
        tinted.fill((100, 150, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._blue_cache[frame_id] = tinted
        return tinted

    def _get_gold_tinted(self, frame):
        frame_id = id(frame)
        if frame_id in self._gold_cache:
            return self._gold_cache[frame_id]
        tinted = frame.copy()
        tinted.fill((255, 200, 50, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._gold_cache[frame_id] = tinted
        return tinted

    def _get_red_tinted(self, frame):
        frame_id = id(frame)
        if frame_id in self._red_cache:
            return self._red_cache[frame_id]
        tinted = frame.copy()
        mask = pygame.mask.from_surface(tinted)
        red_overlay = mask.to_surface(setcolor=(255, 0, 0, 150), unsetcolor=(0, 0, 0, 0))
        tinted.blit(red_overlay, (0, 0))
        self._red_cache[frame_id] = tinted
        return tinted

    def get_attack_hitbox(self, salve=1):
        """Hitbox d'attaque en arc devant le boss, ajustée par salve."""
        if salve <= 2:
            # Salves 1 & 2 : faux proche du corps, portée courte
            range_attack = 25
            width_attack = 30
        else:
            # Salve 3 : grand arc final, portée longue mais étroit (centré sur la lame)
            range_attack = 35
            width_attack = 16
        attack_rect = pygame.Rect(0, 0, range_attack, width_attack)
        if self.facing == 'right':
            attack_rect.left = self.feet.right - 5
        else:
            attack_rect.right = self.feet.left + 5
        attack_rect.centery = self.feet.centery
        return attack_rect

    def update(self, player, walls, player2=None):
        if self.state == 'death':
            self.animate()
            return

        # Paralysie
        if self.paralyzed:
            if pygame.time.get_ticks() >= self.paralyze_end_time:
                self.paralyzed = False
                self._zhonya_gold = False
            else:
                self.velocity.xy = 0, 0
                self.animate()
                return

        current_time = pygame.time.get_ticks()

        # Trouver le joueur le plus proche
        target = player
        if player2 and player2.health > 0:
            d1 = pygame.math.Vector2(player.feet.center).distance_to(self.feet.center) if player.health > 0 else float('inf')
            d2 = pygame.math.Vector2(player2.feet.center).distance_to(self.feet.center)
            if d2 < d1:
                target = player2

        target_center = pygame.math.Vector2(target.feet.center)
        my_center = pygame.math.Vector2(self.feet.center)
        target_vector = target_center - my_center
        distance = target_vector.length()

        # --- Dialogue ---
        if not self.dialogue_finished and self.dialogue_lines:
            if not self.in_dialogue:
                if distance < self.dialogue_zone and target.health > 0:
                    self.in_dialogue = True
                    self.invulnerable = True
                    self.dialogue_index = 0
                    self.dialogue_start_time = current_time
            if self.in_dialogue:
                self.velocity.xy = 0, 0
                self.state = 'idle'
                if target.feet.centerx > self.feet.centerx:
                    self.facing = 'right'
                else:
                    self.facing = 'left'
                _, duration = self.dialogue_lines[self.dialogue_index]
                if current_time - self.dialogue_start_time >= duration:
                    self.dialogue_index += 1
                    self.dialogue_start_time = current_time
                    if self.dialogue_index >= len(self.dialogue_lines):
                        self.in_dialogue = False
                        self.dialogue_finished = True
                        self.invulnerable = False
                        self.has_aggro = True
                        self.activation_played = True
                        self.bgm_playing = True
                        self.pending_sounds.append('boss_activation')
                        self.pending_sounds.append('king_bgm_start')
                self.animate()
                return

        if self.dialogue_lines and not self.dialogue_finished:
            self.animate()
            return

        # --- Aggro ---
        if distance < self.aggro_radius and target.health > 0:
            if not self.has_aggro:
                self.has_aggro = True
                if not self.activation_played:
                    self.activation_played = True
                    self.pending_sounds.append('boss_activation')
                if not self.bgm_playing:
                    self.bgm_playing = True
                    self.pending_sounds.append('king_bgm_start')
        elif target.health <= 0:
            self.has_aggro = False
            if self.bgm_playing:
                self.bgm_playing = False
                self.pending_sounds.append('boss_bgm_stop')

        # --- Compétences ---
        hp_ratio = self.health / self.max_health

        # Compétence 2 : Stun global (prioritaire, seuil 90%)
        if (not self.is_attacking and not self.is_healing and not self.is_praying
                and hp_ratio <= self.stun_threshold and self.has_aggro
                and current_time - self.last_stun_time >= self.stun_cooldown):
            self.is_praying = True
            self.state = 'pray'
            self.frame_index = 0
            self.velocity.xy = 0, 0
            self.last_stun_time = current_time
            self.pray_stun_applied = False
            self.animate()
            return

        # Compétence 1 : Régénération (seuil 70%)
        if (not self.is_attacking and not self.is_healing and not self.is_praying
                and hp_ratio <= self.regen_threshold and self.has_aggro
                and current_time - self.last_regen_time >= self.regen_cooldown):
            self.is_healing = True
            self.state = 'health'
            self.frame_index = 0
            self.velocity.xy = 0, 0
            self.last_regen_time = current_time
            self.animate()
            return

        # Animation de heal en cours
        if self.is_healing:
            self.velocity.xy = 0, 0
            self.animate()
            return

        # Animation de pray en cours
        if self.is_praying:
            self.velocity.xy = 0, 0
            # Appliquer le stun à mi-animation
            anim = self.animations[self.facing].get('pray', [])
            mid = len(anim) // 2 if anim else 4
            if int(self.frame_index) >= mid and not self.pray_stun_applied:
                self.pray_stun_applied = True
                self.pending_global_stun = True
            self.animate()
            return

        # --- Combat ---
        hit_x = False
        hit_y = False
        norm_dir = pygame.math.Vector2(0, 0)

        if self.is_attacking:
            self.velocity.xy = 0, 0
            current_frame = int(self.frame_index)

            # 3 salves de dégâts aux frames 2, 4 et 6
            if current_frame in self._damage_frames and current_frame not in self._dealt_frames:
                self._dealt_frames.add(current_frame)
                # Salve 1=frame2, salve 2=frame4, salve 3=frame6
                salve_num = {2: 1, 4: 2, 6: 3}[current_frame]
                salve_dmg = 5 if salve_num <= 2 else 8  # salve 3 fait + de dégâts
                self.pending_sounds.append('boss_attack')
                attack_area = self.get_attack_hitbox(salve=salve_num)
                # Dégâts au joueur 1
                if player.health > 0 and attack_area.colliderect(player.feet.inflate(20, 20)):
                    player.damage(salve_dmg, source_enemy=self)
                # Dégâts au joueur 2
                if player2 and player2.health > 0 and attack_area.colliderect(player2.feet.inflate(20, 20)):
                    player2.damage(salve_dmg, source_enemy=self)
        else:
            if target.health > 0:
                if target.feet.centerx > self.feet.centerx:
                    self.facing = 'right'
                else:
                    self.facing = 'left'

                attack_area = self.get_attack_hitbox()
                if attack_area.colliderect(target.feet.inflate(20, 20)):
                    if current_time - self.last_attack_time > self.attack_cooldown:
                        self.is_attacking = True
                        self.state = 'attack'
                        self.frame_index = 0
                        self.last_attack_time = current_time
                        self.has_dealt_damage = False
                        self._dealt_frames = set()
                        self.velocity.xy = 0, 0
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

        # --- Mouvement avec collisions ---
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

    def animate(self):
        animation = self.animations[self.facing].get(self.state,
                        self.animations[self.facing].get('idle', []))
        if not animation:
            return

        # Paralysie
        if self.paralyzed:
            idx = max(0, min(int(self.frame_index), len(animation) - 1))
            base = animation[idx]
            if self._is_blinking and pygame.time.get_ticks() - self.hit_time < 150:
                self.image = self._get_red_tinted(base)
            else:
                if pygame.time.get_ticks() - self.hit_time >= 150:
                    self._is_blinking = False
                if self._zhonya_gold:
                    self.image = self._get_gold_tinted(base)
                else:
                    self.image = self._get_blue_tinted(base)
            return

        speed = self.animation_speed
        if self.state == 'death':
            speed = 0.1

        self.frame_index += speed

        if self.frame_index >= len(animation):
            if self.state == 'death':
                self.frame_index = len(animation) - 1
                self._is_blinking = False
            elif self.state == 'attack':
                self.is_attacking = False
                self.state = 'idle'
                self.frame_index = 0
            elif self.state == 'health':
                # Régénération terminée : soigner 25% des PV manquants
                missing = self.max_health - self.health
                self.health = min(self.max_health, self.health + missing * 0.25)
                self.is_healing = False
                self.state = 'idle'
                self.frame_index = 0
            elif self.state == 'pray':
                self.is_praying = False
                self.state = 'idle'
                self.frame_index = 0
            else:
                self.frame_index = 0

        animation = self.animations[self.facing].get(self.state,
                        self.animations[self.facing].get('idle', []))
        if not animation:
            return
        base_frame = animation[int(self.frame_index) % len(animation)]

        if self.state == 'death':
            self._is_blinking = False

        if self._is_blinking:
            if pygame.time.get_ticks() - self.hit_time < 150:
                self.image = self._get_red_tinted(base_frame)
            else:
                self._is_blinking = False
                self.image = base_frame.copy()
        else:
            self.image = base_frame.copy()

    def update_volumes(self, music_vol, sfx_vol):
        pygame.mixer.music.set_volume(music_vol)


# ==========================================
# BOSS 5 : SBIRE DU NEANT
# ==========================================

class SbireNeant(pygame.sprite.Sprite):
    """Boss Sbire du neant. Rapide, teleportation, canalisation de soin."""

    SPRITE_PATH = "assets/images/NightBorne.png"
    FRAME_SIZE = 80  # 80x80 par frame
    COLS = 23
    ROW_FRAMES = {0: 9, 1: 6, 2: 12, 3: 5, 4: 23}

    def __init__(self, x, y):
        super().__init__()
        self.scale_factor = 2.0
        self.animations = {'right': {}, 'left': {}}
        self.state = 'idle'
        self.frame_index = 0
        self.animation_speed = 0.15

        self._load_spritesheet()

        self.image = self.animations['right']['idle'][0]
        self.rect = self.image.get_rect()

        hitbox_width = int(14 * self.scale_factor)
        hitbox_height = int(10 * self.scale_factor)
        self.feet = pygame.Rect(0, 0, hitbox_width, hitbox_height)

        self.y_offset = int(12 * self.scale_factor)

        self.position = pygame.math.Vector2(x, y)
        self.feet.midbottom = (round(self.position.x), round(self.position.y))
        self.rect.centerx = self.feet.centerx
        self.rect.bottom = self.feet.bottom + self.y_offset

        # Stats
        self.max_health = 586
        self.health = 586
        self.speed = 2.5
        self.damage_amount = 8

        self.aggro_radius = 300

        self.velocity = pygame.math.Vector2(0, 0)
        self.facing = "right"

        self.is_attacking = False
        self.last_attack_time = 0
        self.attack_cooldown = 1000
        self.has_dealt_damage = False

        self.has_aggro = False
        self.pending_drop = None
        self._is_blinking = False
        self.hit_time = 0

        self.slide_dir_x = 1
        self.slide_dir_y = 1

        # Teleportation (integree a l'attaque)
        self.pending_teleports = []
        self._has_teleported_attack = False

        # Canalisation de soin
        self.channel_cooldown = 16000
        self.last_channel_time = -20000
        self.channel_threshold = 0.50
        self.is_channeling = False
        self.channel_start_time = 0
        self.channel_last_tick = 0

        # Dialogue de boss
        self.dialogue_lines = [
            ("J'ai ete envoye par le neant pour mettre la main sur l'ether.", 5000),
            ("Je vois que nous partageons le meme dessein...", 4000),
            ("Je vais devoir vous reduire en poussiere.", 4000),
        ]
        self.dialogue_zone = int(self.aggro_radius * 0.40)
        self.in_dialogue = False
        self.dialogue_finished = False
        self.dialogue_index = 0
        self.dialogue_start_time = 0
        self.invulnerable = False
        self.boss_display_name = "Sbire du neant"

        # Sons
        self.activation_played = False
        self.death_sound_played = False
        self.bgm_playing = False
        self.pending_sounds = []

        # Paralysie / stun
        self.paralyzed = False
        self.paralyze_end_time = 0
        self._blue_cache = {}
        self._gold_cache = {}
        self._red_cache = {}
        self._zhonya_gold = False

    def _load_spritesheet(self):
        """Charge toutes les animations depuis NightBorne.png."""
        try:
            sheet = ResourceManager.get_image(self.SPRITE_PATH)
        except FileNotFoundError:
            print(f"Erreur: {self.SPRITE_PATH} introuvable.")
            return

        fs = self.FRAME_SIZE
        nw = int(fs * self.scale_factor)
        nh = int(fs * self.scale_factor)

        anim_map = {
            0: 'idle',
            1: 'run',
            2: 'attack',
            4: 'death',
        }

        for row, state_name in anim_map.items():
            num_frames = self.ROW_FRAMES.get(row, 0)
            frames_right = []
            frames_left = []
            for c in range(num_frames):
                frame = sheet.subsurface((c * fs, row * fs, fs, fs))
                frame = pygame.transform.scale(frame, (nw, nh))
                frames_right.append(frame)
                frames_left.append(pygame.transform.flip(frame, True, False))
            self.animations['right'][state_name] = frames_right
            self.animations['left'][state_name] = frames_left

    def damage(self, amount):
        if self.in_dialogue or self.invulnerable:
            return
        if self.health > 0 and self.state != 'death':
            self.health -= amount
            self._is_blinking = True
            self.hit_time = pygame.time.get_ticks()

            if self.is_channeling:
                self.is_channeling = False

            if self.health <= 0:
                self.health = 0
                self.state = 'death'
                self.frame_index = 0
                self.is_attacking = False
                self.is_channeling = False
                self.velocity.xy = 0, 0
                self._is_blinking = False
                if not self.death_sound_played:
                    self.death_sound_played = True
                    self.pending_sounds.append('boss_death')
                if self.bgm_playing:
                    self.bgm_playing = False
                    self.pending_sounds.append('boss_bgm_stop')

    def get_current_dialogue(self):
        if self.in_dialogue and self.dialogue_index < len(self.dialogue_lines):
            return self.dialogue_lines[self.dialogue_index][0]
        return None

    def skip_dialogue(self):
        if not self.in_dialogue:
            return False
        self.dialogue_index += 1
        self.dialogue_start_time = pygame.time.get_ticks()
        if self.dialogue_index >= len(self.dialogue_lines):
            self.in_dialogue = False
            self.dialogue_finished = True
            self.invulnerable = False
            self.has_aggro = True
            if not self.activation_played:
                self.activation_played = True
                self.pending_sounds.append('boss_activation')
            if not self.bgm_playing:
                self.bgm_playing = True
                self.pending_sounds.append('sbire_bgm_start')
        return True

    def paralyze(self, duration_ms):
        if self.in_dialogue or not self.dialogue_finished:
            return
        self.paralyzed = True
        self.paralyze_end_time = pygame.time.get_ticks() + duration_ms
        if self.is_channeling:
            self.is_channeling = False

    def _get_blue_tinted(self, frame):
        frame_id = id(frame)
        if frame_id in self._blue_cache:
            return self._blue_cache[frame_id]
        tinted = frame.copy()
        tinted.fill((100, 150, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._blue_cache[frame_id] = tinted
        return tinted

    def _get_gold_tinted(self, frame):
        frame_id = id(frame)
        if frame_id in self._gold_cache:
            return self._gold_cache[frame_id]
        tinted = frame.copy()
        tinted.fill((255, 200, 50, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self._gold_cache[frame_id] = tinted
        return tinted

    def _get_red_tinted(self, frame):
        frame_id = id(frame)
        if frame_id in self._red_cache:
            return self._red_cache[frame_id]
        tinted = frame.copy()
        mask = pygame.mask.from_surface(tinted)
        red_overlay = mask.to_surface(setcolor=(255, 0, 0, 150), unsetcolor=(0, 0, 0, 0))
        tinted.blit(red_overlay, (0, 0))
        self._red_cache[frame_id] = tinted
        return tinted

    def get_attack_hitbox(self):
        range_attack = 40
        width_attack = 35
        attack_rect = pygame.Rect(0, 0, range_attack, width_attack)
        if self.facing == 'right':
            attack_rect.left = self.feet.right - 5
        else:
            attack_rect.right = self.feet.left + 5
        attack_rect.centery = self.feet.centery
        return attack_rect

    def update(self, player, walls, player2=None):
        if self.state == 'death':
            self.animate()
            return

        if self.paralyzed:
            if pygame.time.get_ticks() >= self.paralyze_end_time:
                self.paralyzed = False
                self._zhonya_gold = False
            else:
                self.velocity.xy = 0, 0
                self.animate()
                return

        current_time = pygame.time.get_ticks()

        target = player
        if player2 and player2.health > 0:
            d1 = pygame.math.Vector2(player.feet.center).distance_to(self.feet.center) if player.health > 0 else float('inf')
            d2 = pygame.math.Vector2(player2.feet.center).distance_to(self.feet.center)
            if d2 < d1:
                target = player2

        target_center = pygame.math.Vector2(target.feet.center)
        my_center = pygame.math.Vector2(self.feet.center)
        target_vector = target_center - my_center
        distance = target_vector.length()

        # --- Dialogue ---
        if not self.dialogue_finished and self.dialogue_lines:
            if not self.in_dialogue:
                if distance < self.dialogue_zone and target.health > 0:
                    self.in_dialogue = True
                    self.invulnerable = True
                    self.dialogue_index = 0
                    self.dialogue_start_time = current_time
            if self.in_dialogue:
                self.velocity.xy = 0, 0
                self.state = 'idle'
                if target.feet.centerx > self.feet.centerx:
                    self.facing = 'right'
                else:
                    self.facing = 'left'
                _, duration = self.dialogue_lines[self.dialogue_index]
                if current_time - self.dialogue_start_time >= duration:
                    self.dialogue_index += 1
                    self.dialogue_start_time = current_time
                    if self.dialogue_index >= len(self.dialogue_lines):
                        self.in_dialogue = False
                        self.dialogue_finished = True
                        self.invulnerable = False
                        self.has_aggro = True
                        self.activation_played = True
                        self.bgm_playing = True
                        self.pending_sounds.append('boss_activation')
                        self.pending_sounds.append('sbire_bgm_start')
                self.animate()
                return

        if self.dialogue_lines and not self.dialogue_finished:
            self.animate()
            return

        # --- Aggro ---
        if distance < self.aggro_radius and target.health > 0:
            if not self.has_aggro:
                self.has_aggro = True
                if not self.activation_played:
                    self.activation_played = True
                    self.pending_sounds.append('boss_activation')
                if not self.bgm_playing:
                    self.bgm_playing = True
                    self.pending_sounds.append('sbire_bgm_start')
        elif target.health <= 0:
            self.has_aggro = False
            if self.bgm_playing:
                self.bgm_playing = False
                self.pending_sounds.append('boss_bgm_stop')

        # --- Canalisation de soin ---
        hp_ratio = self.health / self.max_health
        if (not self.is_attacking and not self.is_channeling
                and hp_ratio <= self.channel_threshold and self.has_aggro
                and current_time - self.last_channel_time >= self.channel_cooldown):
            self.is_channeling = True
            self.state = 'idle'
            self.frame_index = 0
            self.velocity.xy = 0, 0
            self.channel_start_time = current_time
            self.channel_last_tick = current_time
            self.last_channel_time = current_time

        if self.is_channeling:
            self.velocity.xy = 0, 0
            self.state = 'idle'

            elapsed = current_time - self.channel_last_tick
            if elapsed >= 100:
                heal_amount = self.max_health * 0.10 * (elapsed / 1000.0)
                self.health = min(self.max_health, self.health + heal_amount)
                self.channel_last_tick = current_time

            if self.health >= self.max_health:
                self.health = self.max_health
                self.is_channeling = False

            self.animate()
            return

        # --- Combat ---
        hit_x = False
        hit_y = False
        norm_dir = pygame.math.Vector2(0, 0)

        if self.is_attacking:
            self.velocity.xy = 0, 0
            current_frame = int(self.frame_index)

            # Frame 7 : chance 1/2 de teleportation sur le joueur cible juste avant la salve
            if current_frame >= 7 and not self._has_teleported_attack:
                self._has_teleported_attack = True
                import random as _rnd
                atk_target = target
                if atk_target.health > 0 and _rnd.random() < 0.5:
                    tp_target = pygame.math.Vector2(atk_target.feet.center)
                    tp_from = pygame.math.Vector2(self.feet.centerx, self.feet.bottom)

                    # Orienter vers le joueur
                    if atk_target.feet.centerx > self.feet.centerx:
                        self.facing = 'right'
                    else:
                        self.facing = 'left'

                    # Se placer a portee d'attaque du joueur
                    offset_x = 25 if self.facing == 'right' else -25
                    new_x = atk_target.feet.centerx - offset_x
                    new_y = atk_target.feet.bottom

                    from_x = self.feet.centerx
                    from_y = self.feet.bottom

                    self.position.x = new_x
                    self.position.y = new_y
                    self.feet.centerx = round(self.position.x)
                    self.feet.bottom = round(self.position.y)

                    # Verifier collision mur
                    blocked = False
                    for wall in walls:
                        if self.feet.colliderect(wall):
                            blocked = True
                            break
                    if blocked:
                        self.position.x = from_x
                        self.position.y = from_y
                        self.feet.centerx = round(from_x)
                        self.feet.bottom = round(from_y)
                    else:
                        self.rect.centerx = self.feet.centerx
                        self.rect.bottom = self.feet.bottom + self.y_offset
                        self.pending_teleports.append((from_x, from_y,
                                                       self.feet.centerx, self.feet.bottom))

            # Frames 8-10 : salve de degats
            if 8 <= current_frame <= 10 and not self.has_dealt_damage:
                self.has_dealt_damage = True
                self.pending_sounds.append('boss_attack')
                attack_area = self.get_attack_hitbox()
                if player.health > 0 and attack_area.colliderect(player.feet.inflate(20, 20)):
                    player.damage(self.damage_amount, source_enemy=self)
                if player2 and player2.health > 0 and attack_area.colliderect(player2.feet.inflate(20, 20)):
                    player2.damage(self.damage_amount, source_enemy=self)
        else:
            if target.health > 0 and self.has_aggro:
                if target.feet.centerx > self.feet.centerx:
                    self.facing = 'right'
                else:
                    self.facing = 'left'

                attack_area = self.get_attack_hitbox()
                if attack_area.colliderect(target.feet.inflate(20, 20)):
                    if current_time - self.last_attack_time > self.attack_cooldown:
                        self.is_attacking = True
                        self.state = 'attack'
                        self.frame_index = 0
                        self.last_attack_time = current_time
                        self.has_dealt_damage = False
                        self._has_teleported_attack = False
                        self.velocity.xy = 0, 0
                    else:
                        self.state = 'idle'
                        self.velocity.xy = 0, 0
                elif distance > 0 and distance < self.aggro_radius:
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

        # --- Mouvement avec collisions ---
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

    def animate(self):
        import math as _math

        animation = self.animations[self.facing].get(self.state,
                        self.animations[self.facing].get('idle', []))
        if not animation:
            return

        if self.paralyzed:
            idx = max(0, min(int(self.frame_index), len(animation) - 1))
            base = animation[idx]
            if self._is_blinking and pygame.time.get_ticks() - self.hit_time < 150:
                self.image = self._get_red_tinted(base)
            else:
                if pygame.time.get_ticks() - self.hit_time >= 150:
                    self._is_blinking = False
                if self._zhonya_gold:
                    self.image = self._get_gold_tinted(base)
                else:
                    self.image = self._get_blue_tinted(base)
            return

        speed = self.animation_speed
        if self.state == 'death':
            speed = 0.12

        self.frame_index += speed

        if self.frame_index >= len(animation):
            if self.state == 'death':
                self.frame_index = len(animation) - 1
                self._is_blinking = False
            elif self.state == 'attack':
                self.is_attacking = False
                self.state = 'idle'
                self.frame_index = 0
            else:
                self.frame_index = 0

        animation = self.animations[self.facing].get(self.state,
                        self.animations[self.facing].get('idle', []))
        if not animation:
            return
        base_frame = animation[int(self.frame_index) % len(animation)]

        if self.state == 'death':
            self._is_blinking = False

        # Effet visuel de canalisation : pulsation violette
        if self.is_channeling:
            if self._is_blinking and pygame.time.get_ticks() - self.hit_time < 150:
                self.image = self._get_red_tinted(base_frame)
            else:
                if pygame.time.get_ticks() - self.hit_time >= 150:
                    self._is_blinking = False
                # Pulsation violette uniquement sur les pixels du sprite (via mask)
                t = pygame.time.get_ticks()
                pulse = abs(_math.sin(t * 0.005))
                alpha = int(60 + pulse * 100)
                frame = base_frame.copy()
                mask = pygame.mask.from_surface(frame)
                purple_overlay = mask.to_surface(
                    setcolor=(150, 80, 255, alpha), unsetcolor=(0, 0, 0, 0))
                frame.blit(purple_overlay, (0, 0))
                self.image = frame
            return

        if self._is_blinking:
            if pygame.time.get_ticks() - self.hit_time < 150:
                self.image = self._get_red_tinted(base_frame)
            else:
                self._is_blinking = False
                self.image = base_frame.copy()
        else:
            self.image = base_frame.copy()

    def update_volumes(self, music_vol, sfx_vol):
        pygame.mixer.music.set_volume(music_vol)


