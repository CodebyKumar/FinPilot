from pathlib import Path
import re
html = Path('index.html').read_text(encoding='utf-8')
match = re.search(r'<script>(.*)</script>', html, re.S)
if not match:
    raise SystemExit('No inline script found')
Path('tmp_check.js').write_text(match.group(1), encoding='utf-8')
print('script extracted to tmp_check.js')
