"""slides.json을 편집한 후 실행: 런타임과 대본을 함께 갱신."""
import json
from pathlib import Path
p=Path(__file__).resolve().parent
slides=json.loads((p/'slides.json').read_text())
(p/'slides.js').write_text('window.SLIDES='+json.dumps(slides,ensure_ascii=False)+';')
(p/'script.md').write_text('# 전력예보 발표 대본\n\n약 10분 35초 · 12장 끝 발표자 전환\n\n'+'\n\n'.join(f"## {i+1}. {s['title'].replace(chr(10),' ')} ({s['time']}초)\n\n"+'\n\n'.join('**[→]** '+('**'+n+'**' if i in (0,16) else n) for n in s['notes']) for i,s in enumerate(slides)))
