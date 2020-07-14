from app import app
from src.config import PORT
import user

app.run("0.0.0.0", PORT, debug=True)