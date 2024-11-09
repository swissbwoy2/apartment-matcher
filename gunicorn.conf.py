# Configuration Gunicorn pour l'application Flask
bind = "0.0.0.0:10000"  # Port sur lequel Gunicorn écoutera
workers = 4  # Nombre de workers Gunicorn
timeout = 120  # Timeout en secondes
worker_class = "sync"  # Type de worker
max_requests = 1000  # Nombre maximum de requêtes par worker
max_requests_jitter = 50  # Variation aléatoire du nombre maximum de requêtes
daemon = False  # Ne pas exécuter en arrière-plan
accesslog = "-"  # Logs d'accès sur stdout
errorlog = "-"  # Logs d'erreur sur stderr
loglevel = "info"  # Niveau de log