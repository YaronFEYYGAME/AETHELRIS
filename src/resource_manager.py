import pygame
import os

class ResourceManager:
    """Gestionnaire centralisé pour mettre en cache les images et les polices."""

    _images = {}
    _fonts = {}

    @classmethod
    def get_image(cls, path):
        """
        Charge une image depuis le disque ou la récupère depuis le cache.
        """
        # On standardise le chemin pour éviter les doublons dus aux slashs (Windows/Mac)
        normalized_path = os.path.normpath(path)

        if normalized_path not in cls._images:
            try:
                # On la charge en mémoire UNE SEULE FOIS
                image = pygame.image.load(normalized_path).convert_alpha()
                cls._images[normalized_path] = image
            except FileNotFoundError:
                print(f"⚠️ [ResourceManager] Image introuvable : {path}")
                # En cas d'erreur, on crée un carré violet (texture manquante classique)
                # pour éviter que le jeu ne plante.
                error_surface = pygame.Surface((32, 32))
                error_surface.fill((255, 0, 255))
                cls._images[normalized_path] = error_surface

        return cls._images[normalized_path]

    @classmethod
    def get_font(cls, size, font_name=None):
        """
        Charge une police système ou la récupère depuis le cache.
        SysFont est très lent, donc le cache est crucial ici.
        """
        key = (font_name, size)

        if key not in cls._fonts:
            try:
                cls._fonts[key] = pygame.font.SysFont(font_name, size)
            except Exception as e:
                print(f"⚠️ [ResourceManager] Erreur police {font_name} : {e}")
                # Solution de secours au cas où la police plante
                cls._fonts[key] = pygame.font.Font(None, size)

        return cls._fonts[key]
