import os
import sys
from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    # Running as a packaged .exe
    # 1) First try the bundled .env inside _MEIPASS (packed into the exe)
    bundle_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    bundled_env = os.path.join(bundle_dir, '.env')

    # 2) Also check next to the .exe (user can override by placing .env there)
    exe_dir = os.path.dirname(sys.executable)
    external_env = os.path.join(exe_dir, '.env')

    # Prefer the external file if it exists, otherwise use bundled
    if os.path.exists(external_env):
        env_path = external_env
    else:
        env_path = bundled_env
else:
    # Running normally as a python script
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

# Force dotenv to load exactly from that path
load_dotenv(dotenv_path=env_path)


def get_env_value(key, default=None):
    value = os.getenv(key, default)
    if isinstance(value, str):
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
    return value


DISCORD_TOKEN = get_env_value("DISCORD_TOKEN")
ENV_PATH_USED = env_path
