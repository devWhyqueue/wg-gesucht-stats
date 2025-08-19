import random, time, threading
from collections import defaultdict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import ProxyError, ConnectTimeout, ReadTimeout, SSLError, ConnectionError, RequestException

from wggesuchtstats.config import USER_AGENTS

# --- Tunables ---
PROXY_FILE = "out/working_proxies_all.txt"

PROXY_REMOVE_AFTER = 2
SOFT_EXCLUDE_AFTER = 1
MAX_ATTEMPTS = 200
CONNECT_TIMEOUT = 3
READ_TIMEOUT = 5
MAX_JITTER = 0.15

# --- State ---
proxy_list: list[str] = []
proxy_failure_counts: defaultdict[str, int] = defaultdict(int)
_proxy_lock = threading.RLock()

# --- Session ---
_session = requests.Session()
_session.trust_env = False
_session.headers.update({"Accept-Language": "de-DE,de;q=0.9,en;q=0.8"})
_adapter = HTTPAdapter(
    pool_connections=512,
    pool_maxsize=512,
    max_retries=Retry(total=0, connect=0, read=0, redirect=0),
    pool_block=False,
)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

# --- Helpers ---
def _get_proxies(path: str = PROXY_FILE) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        return [ln.strip() for ln in lines if ln.strip() and ":" in ln]
    except Exception:
        return []

def _remove_failed_proxy_locked(p: str) -> None:
    if p in proxy_list: proxy_list.remove(p)
    proxy_failure_counts.pop(p, None)

def _handle_proxy_failure(p: str | None) -> None:
    if not p: return
    with _proxy_lock:
        c = proxy_failure_counts[p] + 1
        proxy_failure_counts[p] = c
        if c >= PROXY_REMOVE_AFTER: _remove_failed_proxy_locked(p)

def _handle_proxy_success(p: str | None) -> None:
    if not p: return
    with _proxy_lock: proxy_failure_counts[p] = 0

def _ensure_global_proxies() -> None:
    if proxy_list: return
    new_list = _get_proxies()
    with _proxy_lock:
        if not proxy_list and new_list: proxy_list[:] = new_list

def _snapshot_local() -> list[str]:
    with _proxy_lock:
        local = [p for p in proxy_list if proxy_failure_counts[p] < SOFT_EXCLUDE_AFTER]
        return local or proxy_list[:]

def _is_retryable_status(code: int) -> bool:
    return code in (301, 302, 401, 403, 407, 429, 500, 502, 503, 504)

def get_proxy_stats() -> dict:
    with _proxy_lock:
        return {
            "total_proxies": len(proxy_list),
            "healthy_proxies": sum(1 for p in proxy_list if proxy_failure_counts[p] < PROXY_REMOVE_AFTER),
            "failure_counts": dict(proxy_failure_counts),
        }

# --- Public API ---
def requests_get(
    url: str,
    *,
    connect_timeout: int = CONNECT_TIMEOUT,
    read_timeout: int = READ_TIMEOUT,
    max_attempts: int = MAX_ATTEMPTS,
    on_attempt=None,
) -> requests.Response:
    _ensure_global_proxies()
    local = _snapshot_local(); random.shuffle(local)
    attempt, i = 0, 0
    while attempt < max_attempts:
        if i >= len(local):
            _ensure_global_proxies()
            local = _snapshot_local()
            if not local: raise RequestException("No proxies available")
            random.shuffle(local); i = 0
        proxy = local[i]; i += 1; attempt += 1
        if on_attempt: on_attempt(attempt, proxy)
        proxies = {"http": proxy, "https": proxy}
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            r = _session.get(
                url,
                proxies=proxies,
                timeout=(connect_timeout, read_timeout),
                allow_redirects=False,
                headers=headers,
            )
            if _is_retryable_status(r.status_code):
                _handle_proxy_failure(proxy); time.sleep(random.random() * MAX_JITTER); continue
            _handle_proxy_success(proxy); return r
        except (ProxyError, ConnectTimeout, ReadTimeout, SSLError, ConnectionError, RequestException):
            _handle_proxy_failure(proxy); time.sleep(random.random() * MAX_JITTER)
    raise RequestException(f"Failed after {max_attempts} attempts. Stats: {get_proxy_stats()}")
