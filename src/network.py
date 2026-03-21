import socket
import threading
import json
import struct


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def ip_to_code(ip):
    """Retourne le dernier octet de l'IP sous forme d'entier (0-255)."""
    try:
        return int(ip.split('.')[-1])
    except Exception:
        return 0


def send_msg(sock, data):
    """Envoie un dict JSON préfixé de 4 octets (longueur)."""
    raw = json.dumps(data).encode('utf-8')
    sock.sendall(struct.pack('>I', len(raw)) + raw)


def recv_msg(sock):
    """Reçoit un dict JSON préfixé de 4 octets. Retourne None si déconnexion."""
    header = _recv_exact(sock, 4)
    if not header:
        return None
    length = struct.unpack('>I', header)[0]
    raw = _recv_exact(sock, length)
    if not raw:
        return None
    try:
        return json.loads(raw.decode('utf-8'))
    except Exception:
        return None


def _recv_exact(sock, n):
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
        self.client_arrived = False  # True dès qu'un client s'est connecté
        self._running = False

    def start(self):
        """Démarre le serveur (écoute). Non-bloquant : attend le client dans un thread."""
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind(('', self.PORT))
        self._server_sock.listen(1)
        self._server_sock.settimeout(120)
        self._running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def _accept_loop(self):
        try:
            conn, _ = self._server_sock.accept()
            conn.settimeout(5)
            with self._lock:
                self._client_sock = conn
                self.connected = True
                self.client_arrived = True
            self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._recv_thread.start()
        except Exception:
            pass

    def _recv_loop(self):
        while self._running and self.connected:
            try:
                msg = recv_msg(self._client_sock)
                if msg is None:
                    self.connected = False
                    break
                with self._lock:
                    self._inputs = msg.get('inputs', {})
            except Exception:
                self.connected = False
                break

    def send_state(self, state):
        if not self.connected:
            return
        try:
            send_msg(self._client_sock, state)
        except Exception:
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


class GameClient:
    PORT = 5555

    def __init__(self):
        self._sock = None
        self._lock = threading.Lock()
        self._state = {}
        self._recv_thread = None
        self.connected = False
        self._running = False

    def connect(self, host_ip, timeout=5):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host_ip, self.PORT))
            s.settimeout(5)
            self._sock = s
            self.connected = True
            self._running = True
            self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._recv_thread.start()
            return True
        except Exception:
            return False

    def _recv_loop(self):
        while self._running and self.connected:
            try:
                msg = recv_msg(self._sock)
                if msg is None:
                    self.connected = False
                    break
                with self._lock:
                    self._state = msg
            except Exception:
                self.connected = False
                break

    def send_inputs(self, inputs):
        if not self.connected:
            return
        try:
            send_msg(self._sock, {'inputs': inputs})
        except Exception:
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


def scan_for_host(code):
    """Cherche un hôte ayant le dernier octet IP = code sur le sous-réseau local.
    Retourne l'IP si trouvée, None sinon."""
    local_ip = get_local_ip()
    parts = local_ip.split('.')
    if len(parts) != 4:
        return None
    subnet = '.'.join(parts[:3])
    target_ip = f"{subnet}.{code}"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        result = s.connect_ex((target_ip, GameClient.PORT))
        if result == 0:
            return target_ip
    except Exception:
        pass
    finally:
        try:
            s.close()
        except Exception:
            pass
    return None
