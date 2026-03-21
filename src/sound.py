import pygame
import random
import math


# ---------------------------------------------------------------------------
# Constantes de spatialisation
# ---------------------------------------------------------------------------
MIN_DISTANCE = 50      # En dessous → volume 100 %
MAX_DISTANCE = 600     # Au-delà    → volume 0 %
PAN_RANGE    = 300     # Distance horizontale pour le panning max


class SoundManager:
    """Gestionnaire audio avec spatialisation optionnelle.

    Trois modes de lecture :
      1. play_spatial(name, source_pos, listener_pos) — spatialisé (volume + panning)
      2. play_ui_*(…)  — sons d'inventaire / UI, volume fixe, jamais partagés
      3. Musique (pygame.mixer.music) — gérée en dehors, non touchée
    """

    def __init__(self):
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(32)
            self.enabled = True
        except pygame.error:
            self.enabled = False
            print("⚠️ Aucun périphérique audio disponible — le jeu continue sans son.")
        self.sounds = {}
        self.global_sfx_vol = 0.8
        self._next_channel = 0          # round-robin pour les channels

        def load_sound(name, path):
            if not self.enabled:
                return
            try:
                self.sounds[name] = pygame.mixer.Sound(path)
                print(f"Son chargé : {name}")
            except (FileNotFoundError, pygame.error):
                print(f"⚠️ Attention : Fichier son manquant pour '{name}' à l'emplacement : {path}")

        # --- CHARGEMENT DES SONS ---
        load_sound('mmo', "assets/sounds/clear-combo-7-394494-_1_.wav")
        load_sound('step', "assets/sounds/walking-on-concrete-ver-2-268513.wav")
        load_sound('sword', "assets/sounds/sword.wav")
        load_sound('shot', "assets/sounds/shot.wav")
        load_sound('equip_sword', "assets/sounds/sword_inventory.wav")
        load_sound('equip_bow', "assets/sounds/arcbow_inventory.wav")
        load_sound('rock_broke', "assets/sounds/rock_broke.wav")
        load_sound('eureka', "assets/sounds/eureka.mp3")
        load_sound('death', "assets/sounds/death.wav")
        load_sound('eating', "assets/sounds/eating.wav")

        # --- SONS DU DASH ET DE L'ÉQUIPEMENT ---
        load_sound('dash1', "assets/sounds/dash1.wav")
        load_sound('dash2', "assets/sounds/dash2.wav")
        load_sound('dash3', "assets/sounds/dash3.wav")
        load_sound('equipement', "assets/sounds/equipement.wav")

        # --- SONS DES BOSS ---
        load_sound('boss_activation', "assets/sounds/boss1_activation.wav")
        load_sound('boss_attack', "assets/sounds/boss1_attack.wav")
        load_sound('boss_death', "assets/sounds/boss1_death.wav")
        load_sound('boss_talk', "assets/sounds/boss1_talk.wav")

        self.base_volumes = {
            'step': 0.4,
            'equip_sword': 0.3,
            'equip_bow': 0.3,
            'eureka': 0.6,
            'death': 0.5,
            'sword': 0.3,
            'mmo': 0.7,
            'shot': 0.6,
            'rock_broke': 0.8,
            'eating': 0.8,
            'dash1': 0.6,
            'dash2': 0.6,
            'dash3': 0.6,
            'equipement': 0.6,
            'boss_activation': 0.4,
            'boss_attack': 0.4,
            'boss_death': 0.45,
            'boss_talk': 0.35,
        }

        self.update_sfx_volume(0.8)

    # ------------------------------------------------------------------
    # Volume global
    # ------------------------------------------------------------------
    def update_sfx_volume(self, global_vol):
        self.global_sfx_vol = global_vol
        for name, sound in self.sounds.items():
            base = self.base_volumes.get(name, 1.0)
            sound.set_volume(base * global_vol)

    # ------------------------------------------------------------------
    # Calcul de spatialisation
    # ------------------------------------------------------------------
    @staticmethod
    def _compute_spatial(source_pos, listener_pos):
        """Retourne (volume, left_factor, right_factor) entre 0 et 1."""
        dx = source_pos[0] - listener_pos[0]
        dy = source_pos[1] - listener_pos[1]
        distance = math.hypot(dx, dy)

        # Atténuation linéaire
        if distance <= MIN_DISTANCE:
            volume = 1.0
        elif distance >= MAX_DISTANCE:
            volume = 0.0
        else:
            volume = 1.0 - (distance - MIN_DISTANCE) / (MAX_DISTANCE - MIN_DISTANCE)

        # Panning stéréo
        pan = max(-1.0, min(1.0, dx / PAN_RANGE)) if PAN_RANGE > 0 else 0.0
        left_factor  = max(0.3, 1.0 - max(0.0, pan))
        right_factor = max(0.3, 1.0 + min(0.0, pan))

        return volume, left_factor, right_factor

    def _get_channel(self):
        """Retourne un channel libre en round-robin."""
        if not self.enabled:
            return None
        total = pygame.mixer.get_num_channels()
        for _ in range(total):
            ch = pygame.mixer.Channel(self._next_channel % total)
            self._next_channel = (self._next_channel + 1) % total
            if not ch.get_busy():
                return ch
        # Tous occupés → prend le prochain quand même (interrompt)
        ch = pygame.mixer.Channel(self._next_channel % total)
        self._next_channel = (self._next_channel + 1) % total
        return ch

    # ------------------------------------------------------------------
    # LECTURE SPATIALISÉE — pour tous les SFX du jeu
    # ------------------------------------------------------------------
    def play_spatial(self, sound_name, source_pos, listener_pos):
        """Joue un son avec volume et panning ajustés à la distance.

        sound_name : clé du son (ex. 'sword', 'boss_attack', 'dash1'…)
        source_pos : (x, y) position de la source dans le monde
        listener_pos : (x, y) position du joueur local
        """
        if not self.enabled:
            return
        sound = self.sounds.get(sound_name)
        if not sound:
            return

        volume, left_f, right_f = self._compute_spatial(source_pos, listener_pos)
        if volume <= 0.0:
            return  # trop loin, on ne joue rien

        base = self.base_volumes.get(sound_name, 1.0)
        final_vol = base * self.global_sfx_vol * volume

        ch = self._get_channel()
        if ch:
            ch.play(sound)
            ch.set_volume(final_vol * left_f, final_vol * right_f)

    def play_spatial_dash(self, source_pos, listener_pos):
        """Joue un son de dash aléatoire spatialisé."""
        dash_keys = [k for k in self.sounds if k.startswith('dash')]
        if dash_keys:
            self.play_spatial(random.choice(dash_keys), source_pos, listener_pos)

    # ------------------------------------------------------------------
    # LECTURE UI / INVENTAIRE — volume fixe, personnel, jamais partagé
    # ------------------------------------------------------------------
    def play_ui_equip_sword(self):
        if 'equip_sword' in self.sounds: self.sounds['equip_sword'].play()

    def play_ui_equip_bow(self):
        if 'equip_bow' in self.sounds: self.sounds['equip_bow'].play()

    def play_ui_equipement(self):
        if 'equipement' in self.sounds: self.sounds['equipement'].play()

    def play_ui_eating(self):
        if 'eating' in self.sounds: self.sounds['eating'].play()

    # ------------------------------------------------------------------
    # LECTURE DIRECTE (non spatialisée) — sons personnels du joueur
    # ------------------------------------------------------------------
    def play_step(self):
        if 'step' in self.sounds: self.sounds['step'].play(-1)

    def stop_step(self):
        if 'step' in self.sounds: self.sounds['step'].stop()

    def play_death(self):
        if 'death' in self.sounds: self.sounds['death'].play()

    def play_mmo_sound(self):
        if 'mmo' in self.sounds: self.sounds['mmo'].play()

    # ------------------------------------------------------------------
    # Anciens play_* gardés pour compatibilité (non spatialisés)
    # ------------------------------------------------------------------
    def play_sword_sound(self):
        if 'sword' in self.sounds: self.sounds['sword'].play()

    def play_projectile_sound(self):
        if 'shot' in self.sounds: self.sounds['shot'].play()

    def play_equip_sword(self):
        if 'equip_sword' in self.sounds: self.sounds['equip_sword'].play()

    def play_equip_bow(self):
        if 'equip_bow' in self.sounds: self.sounds['equip_bow'].play()

    def play_rock_broke(self):
        if 'rock_broke' in self.sounds: self.sounds['rock_broke'].play()

    def play_eureka(self):
        if 'eureka' in self.sounds: self.sounds['eureka'].play()

    def play_eating(self):
        if 'eating' in self.sounds: self.sounds['eating'].play()

    def play_dash_sound(self):
        dash_sounds = [s for k, s in self.sounds.items() if k.startswith('dash')]
        if dash_sounds:
            random.choice(dash_sounds).play()

    def play_equipement(self):
        if 'equipement' in self.sounds: self.sounds['equipement'].play()

    # --- SONS DES BOSS ---
    def play_boss_activation(self):
        if 'boss_activation' in self.sounds: self.sounds['boss_activation'].play()

    def play_boss_attack(self):
        if 'boss_attack' in self.sounds: self.sounds['boss_attack'].play()

    def play_boss_death(self):
        if 'boss_death' in self.sounds: self.sounds['boss_death'].play()

    def play_boss_talk(self):
        if 'boss_talk' in self.sounds: self.sounds['boss_talk'].play()
