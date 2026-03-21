import pygame
import random

class SoundManager:
    def __init__(self):
        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            self.enabled = False
            print("⚠️ Aucun périphérique audio disponible — le jeu continue sans son.")
        self.sounds = {}

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
        load_sound('equipement', "assets/sounds/equipement.wav") # NOUVEAU SON

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
            'equipement': 0.6 # Volume de base de l'équipement
        }

        self.update_sfx_volume(0.8)

    def update_sfx_volume(self, global_vol):
        for name, sound in self.sounds.items():
            base = self.base_volumes.get(name, 1.0)
            sound.set_volume(base * global_vol)

    def play_step(self):
        if 'step' in self.sounds: self.sounds['step'].play(-1)

    def stop_step(self):
        if 'step' in self.sounds: self.sounds['step'].stop()

    def play_mmo_sound(self):
        if 'mmo' in self.sounds: self.sounds['mmo'].play()
        
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
        
    def play_death(self):
        if 'death' in self.sounds: self.sounds['death'].play()
        
    def play_eating(self):
        if 'eating' in self.sounds: self.sounds['eating'].play()
        
    def play_dash_sound(self):
        dash_sounds = [s for k, s in self.sounds.items() if k.startswith('dash')]
        if dash_sounds:
            random.choice(dash_sounds).play()

    # --- NOUVELLE FONCTION ---
    def play_equipement(self):
        if 'equipement' in self.sounds: self.sounds['equipement'].play()