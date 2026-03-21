import socket
import threading
import json
import struct


def get_local_ip():
    """Retourne l'IP locale de cette machine sur le réseau."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def ip_to_code(ip):
    """Retourne le dernier octet de l'IP (0-255)."""
    try:
        return int(ip.split('.')[-1])
    except Exception:
        return 0


def resolve_host(input_str):
    """Convertit un code (3 chiffres) ou une IP complète en adresse IP.

    - "047"          → "192.168.X.47"   (reconstruit depuis le sous-réseau local)
    - "192.168.1.47" → "192.168.1.47"   (renvoyé tel quel)

    Ne fait AUCUNE connexion réseau — pure reconstruction de chaîne.
    Retourne None si l'entrée est invalide.
    """
    inp = input_str.strip()
    if not inp:
        return None

    # IP complète (contient des points)
    if '.' in inp:
        parts = inp.split('.')
        if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            return inp
        return None

    # Code à 3 chiffres (dernier octet)
    if inp.isdigit() and len(inp) <= 3:
        code = int(inp)
        if not (0 <= code <= 255):
            return None
        local_ip = get_local_ip()
        parts = local_ip.split('.')
        if len(parts) != 4:
            return None
        subnet = '.'.join(parts[:3])
        return f"{subnet}.{code}"

    return None


def send_msg(sock, data):
    """Envoie un dict JSON préfixé de 4 octets (longueur big-endian)."""
    raw = json.dumps(data).encode('utf-8')
    sock.sendall(struct.pack('>I', len(raw)) + raw)


def recv_msg(sock):
    """Reçoit un dict JSON préfixé de 4 octets. Retourne None si déconnexion."""
    header = _recv_exact(sock, 4)
    if not header:
        return None
    length = struct.unpack('>I', header)[0]
    # Sanité : un message > 10 Mo est suspect
    if length > 10 * 1024 * 1024:
        return None
    raw = _recv_exact(sock, length)
    if not raw:
        return None
    try:
        return json.loads(raw.decode('utf-8'))
    except Exception:
        return None


def _recv_exact(sock, n):
    """Lit exactement n octets depuis le socket. Retourne None si fermeture."""
    data = b''
    while len(data) < n:
        try:
            chunk = sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        except Exception:
            return None
    return data


# =============================================================================
# SERVEUR
# =============================================================================

class GameServer:
    PORT = 5555

    def __init__(self):
        self._server_sock = None
        self._client_sock = None
        self._lock = threading.Lock()
        self._inputs = {}
        self._recv_thread = None
        self._accept_thread = None
        self.connected = False
        self.client_arrived = False
        self._running = False
        self.last_error = ""

    def start(self):
        """Démarre l'écoute TCP. Non-bloquant : l'acceptation se fait dans un thread."""
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind(('', self.PORT))
        self._server_sock.listen(1)
        # Timeout sur le serveur uniquement pour débloquer stop()
        self._server_sock.settimeout(120)
        self._running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def _accept_loop(self):
        try:
            conn, addr = self._server_sock.accept()
            # Pas de timeout sur le socket de jeu : on veut des recv bloquants
            # dans le thread, la boucle s'arrête proprement quand recv renvoie b"".
            conn.settimeout(None)
            with self._lock:
                self._client_sock = conn
                self.connected = True
                self.client_arrived = True
            self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._recv_thread.start()
        except socket.timeout:
            self.last_error = "Délai d'attente dépassé (120 s) — aucun client connecté"
        except Exception as e:
            if self._running:
                self.last_error = f"Erreur serveur : {e}"

    def _recv_loop(self):
        while self._running and self.connected:
            msg = recv_msg(self._client_sock)
            if msg is None:
                self.connected = False
                break
            with self._lock:
                self._inputs = msg.get('inputs', {})

    def send_state(self, state):
        if not self.connected:
            return
        try:
            send_msg(self._client_sock, state)
        except Exception as e:
            self.last_error = f"Envoi état échoué : {e}"
            self.connected = False

    def get_inputs(self):
        with self._lock:
            return dict(self._inputs)

    def stop(self):
        self._running = False
        self.connected = False
        for s in [self._client_sock, self._server_sock]:
            if s:
                try:
                    s.close()
                except Exception:
                    pass


# =============================================================================
# CLIENT
# =============================================================================

class GameClient:
    PORT = 5555

    def __init__(self):
        self._sock = None
        self._lock = threading.Lock()
        self._state = {}
        self._recv_thread = None
        self.connected = False
        self._running = False
        self.last_error = ""

    def connect(self, host_ip, timeout=5):
        """Tente de se connecter au serveur. Retourne True si réussi."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Timeout uniquement pendant la phase de connexion initiale
            s.settimeout(timeout)
            s.connect((host_ip, self.PORT))
            # Une fois connecté, on passe en mode bloquant pour les recv du thread.
            # Le thread lit en continu ; il s'arrête proprement quand recv → b"".
            s.settimeout(None)
            self._sock = s
            self.connected = True
            self._running = True
            self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._recv_thread.start()
            return True
        except ConnectionRefusedError:
            self.last_error = (
                f"Connexion refusée par {host_ip}:{self.PORT}\n"
                "→ Vérifiez que l'hôte a bien lancé \"Héberger\" avant vous.\n"
                "→ Sur Windows : autorisez Python dans le Pare-feu Windows\n"
                "  (Panneau de config > Pare-feu > Autoriser une application)"
            )
            return False
        except socket.timeout:
            self.last_error = (
                f"Timeout — {host_ip}:{self.PORT} ne répond pas ({timeout} s)\n"
                "→ Vérifiez que les deux PC sont sur le même réseau WiFi.\n"
                "→ Sur Windows : autorisez Python dans le Pare-feu Windows\n"
                f"  Port utilisé : TCP {self.PORT}"
            )
            return False
        except OSError as e:
            self.last_error = (
                f"Erreur réseau : {e}\n"
                f"→ Vérifiez l'IP saisie et le port TCP {self.PORT}"
            )
            return False

    def _recv_loop(self):
        while self._running and self.connected:
            msg = recv_msg(self._sock)
            if msg is None:
                self.connected = False
                break
            with self._lock:
                self._state = msg

    def send_inputs(self, inputs):
        if not self.connected:
            return
        try:
            send_msg(self._sock, {'inputs': inputs})
        except Exception as e:
            self.last_error = f"Envoi inputs échoué : {e}"
            self.connected = False

    def get_state(self):
        with self._lock:
            return dict(self._state)

    def stop(self):
        self._running = False
        self.connected = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
