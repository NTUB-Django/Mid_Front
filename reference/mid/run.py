import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys


for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='replace')


ROOT = Path(__file__).resolve().parent


def execute(command, env):
    subprocess.run([str(value) for value in command], cwd=ROOT, env=env, check=True)


def main():
    parser = argparse.ArgumentParser(description='NTUB Django 期中版：安裝、初始化及本機啟動')
    parser.add_argument('action', nargs='?', default='start', choices=['start', 'setup', 'admin', 'check'])
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--reinstall', action='store_true')
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error('請安裝 Python 3.10 以上版本，建議使用 Python 3.12。')
    if not 1024 <= args.port <= 65535:
        parser.error('連接埠需介於 1024 與 65535。')
    env = os.environ.copy()
    env['PYTHONUTF8'] = '1'
    env['PYTHONUNBUFFERED'] = '1'
    env['DJANGO_DEBUG'] = '1'
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    environment = ROOT / '.venv'
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    valid_environment = python.is_file() and subprocess.run(
        [str(python), '-c', 'import encodings, pip'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0
    if not valid_environment:
        print('正在建立專案專用 Python 環境…', flush=True)
        base_python = Path(getattr(sys, '_base_executable', sys.executable)).resolve()
        execute([base_python, '-m', 'venv', environment], env)
    fingerprint = hashlib.sha256((ROOT / 'requirements.txt').read_bytes()).hexdigest()
    stamp = environment / '.requirements-sha256'
    if args.reinstall or not stamp.is_file() or stamp.read_text().strip() != fingerprint:
        print('正在安裝套件，首次執行需要網路連線…', flush=True)
        execute([python, '-m', 'pip', 'install', '-r', ROOT / 'requirements.txt'], env)
        stamp.write_text(fingerprint, encoding='utf-8')
    execute([python, 'manage.py', 'migrate', '--noinput'], env)
    execute([python, 'manage.py', 'import_courses', '--if-empty'], env)
    execute([python, 'manage.py', 'seed_users'], env)
    if args.action == 'check':
        execute([python, 'manage.py', 'check'], env)
    elif args.action == 'admin':
        execute([python, 'manage.py', 'createsuperuser'], env)
    elif args.action == 'start':
        print(f'網站：http://127.0.0.1:{args.port}/　後台：http://127.0.0.1:{args.port}/admin/', flush=True)
        print('按 Ctrl+C 停止。下次仍使用同一個指令，不會清空既有課表。', flush=True)
        execute([python, 'manage.py', 'runserver', f'127.0.0.1:{args.port}'], env)
    else:
        print('初始化完成。執行 python run.py 即可啟動。', flush=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('已停止。')
    except subprocess.CalledProcessError as error:
        print('執行失敗，請依上方訊息排除問題後重試。', file=sys.stderr)
        raise SystemExit(error.returncode)
    except (OSError, RuntimeError) as error:
        print(f'無法啟動：{error}', file=sys.stderr)
        raise SystemExit(1)
