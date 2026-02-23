import os

# Binding
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Workers
workers = 2
worker_class = "gthread"

# Timeout
timeout = 120

# Logging
accesslog = "-"
errorlog = "-"
