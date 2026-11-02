import ast
import io
from pathlib import Path
import re
import subprocess
import sys
import tokenize


for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='replace')


ROOT = Path(__file__).resolve().parent.parent
SECRET_PATTERNS = [
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(r'\bgh[pousr]_[A-Za-z0-9]{20,}'),
    re.compile(r'\bgithub_pat_[A-Za-z0-9_]{30,}'),
    re.compile(r'\bgsk_[A-Za-z0-9]{25,}'),
    re.compile(r'\bnvapi-[A-Za-z0-9_-]{25,}'),
    re.compile(r'\bsk-proj-[A-Za-z0-9_-]{25,}'),
    re.compile(r'\bAIza[A-Za-z0-9_-]{30,}'),
    re.compile(r'\beyJ[A-Za-z0-9_-]{80,}'),
    re.compile(r'postgres(?:ql)?://[^\s/:]+:[^\s/@]+@'),
    re.compile('/' + r'Users/[^/\s]+/'),
]
FORBIDDEN_PARTS = {'.venv', 'node_modules', '.runtime', '.qa', '.playwright-mcp', '__pycache__', 'backups', 'media', 'staticfiles'}
FORBIDDEN_SUFFIXES = {'.sqlite3', '.db', '.dump', '.sql', '.log', '.pem', '.key', '.p12', '.pfx', '.xlsx', '.docx', '.pptx', '.pdf'}


def main():
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    problems = []
    for name in filter(None, paths):
        path = Path(name)
        if (set(path.parts) & FORBIDDEN_PARTS or path.suffix.lower() in FORBIDDEN_SUFFIXES
                or path.name in {'.env', '.local-secret', 'auth.json', 'token.json', 'tokens.json'}
                or (path.name.startswith('.env.') and path.name != '.env.example')
                or re.search(r'credentials|client_secret', path.name, re.I)):
            problems.append(f'{name}: 不應公開的檔案類型')
        data = (ROOT / path).read_bytes()
        if path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp', '.ico'}:
            continue
        try:
            content = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            problems.append(f'{name}: 無法檢查的二進位檔案')
            continue
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            problems.append(f'{name}: 疑似機密或本機路徑，請人工確認')
        if path.name == '.env.example':
            for line in content.splitlines():
                key, separator, value = line.partition('=')
                if separator and re.search(r'(?:KEY|SECRET|TOKEN|PASSWORD)$', key) and value.strip():
                    problems.append(f'{name}: 金鑰欄位必須留空')
        if path.suffix == '.py':
            try:
                tree = ast.parse(content)
                if any(item.type == tokenize.COMMENT for item in tokenize.generate_tokens(io.StringIO(content).readline)):
                    problems.append(f'{name}: 尚有 Python 註解')
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and ast.get_docstring(node):
                        problems.append(f'{name}: 尚有說明字串')
                        break
            except (SyntaxError, tokenize.TokenError):
                problems.append(f'{name}: Python 語法無法解析')
        if path.suffix in {'.html', '.svg'} and re.search(r'<!--|\{#|\{%\s*comment\s*%\}', content):
            problems.append(f'{name}: 尚有樣板註解')
        if path.suffix in {'.js', '.jsx', '.css', '.html'} and re.search(r'^\s*//|/\*', content, re.M):
            problems.append(f'{name}: 疑似仍有前端註解')
    if problems:
        print('\n'.join(problems), file=sys.stderr)
        raise SystemExit(1)
    print('公開檔案檢查通過：未發現禁止檔案、已知金鑰格式或程式註解。')


if __name__ == '__main__':
    main()
