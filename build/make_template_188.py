"""make_template_188.py: builds build/laf_template.html from the Mott page (mott-167/build/mott_template.html): same styles, charts and
scroll-driven model, with 188 Lafayette's words (laf_body.html), model, camera path and colours."""
import os
S = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(S, '..', '..', 'mott-167', 'build', 'mott_template.html')).read()
head = src[:src.index('<style>')]; css = src[src.index('<style>'):src.index('</style>') + 8]
js = src[src.index('<script>\nconst D = __DATA__'):]
def sub(s, pairs):
    for a, b in pairs:
        assert a in s, a[:80]; s = s.replace(a, b)
    return s
URL = 'https://feldtdesign-ship-it.github.io/broome-413/'
DESC = "413 Broome Street: the small pink corner store at Broome and Lafayette, on the ground floor of the Sing Tao Daily building. The building, the store, what is next door, the trains and the landmark rules, from public data."
head = sub(head, [
 ('<title>One Door of Two</title>', '<title>The Small Pink Store</title>'),
 ('https://feldtdesign-ship-it.github.io/mott-167/og.jpg', URL + 'og.jpg'),
 ('https://feldtdesign-ship-it.github.io/mott-167/', URL),
 ('167 Mott Street · One Door of Two', '413 Broome Street · The Small Pink Store'),
])
import re
head = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{DESC}">', head)
head = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{DESC}">', head)
head = re.sub(r'<meta name="twitter:description" content="[^"]*">', f'<meta name="twitter:description" content="{DESC}">', head)
js = sub(js, [
 ("$('sub').innerHTML=`Entries at Bowery, Spring Street and Grand Street added together and doubled to include exits, summer 2026 average. The nearest stairs are <b>215 m</b> away.",
  "$('sub').innerHTML=`Entries at Spring Street and Canal Street added together and doubled to include exits, summer 2026 average. The nearest stairs are <b>192 m</b> away."),
 ("const MODEL='assets/mott_167.glb';", "const MODEL='assets/lafayette_188.glb';"),
 ("const P=__POINTS__; const DOOR=P.door, N=[0.956,0.292];   // N = the way the front faces, out over Mott Street",
  "const P=__POINTS__; const DOOR=P.door, N=[0.842,0.541];   // N = the way the pink store's Lafayette window faces"),
 ("BOW=G('bowery_jz'), SPR=G('spring_6'), GRD=G('grand_bd'); const MID=[(BOW[0]+SPR[0]+GRD[0])/3,0,(BOW[2]+SPR[2]+GRD[2])/3];",
  "BOW=G('canal_st'), SPR=G('spring_6'), GRD=G('prince_rw'); const MID=[(BOW[0]+SPR[0]+GRD[0])/3,0,(BOW[2]+SPR[2]+GRD[2])/3];"),
 ("if(n.startsWith('NOLITA_MASSING'))", "if(n.startsWith('SOHO_MASSING'))"),
 ("else if(n.startsWith('SITE_167')||n.startsWith('B167_BRICK')){o.castShadow=true;if(m){m.color=new THREE.Color(0x9A6048);m.emissive=new THREE.Color(0x9A6048);m.emissiveIntensity=.38;}}",
  "else if(n.startsWith('SITE_188')){o.castShadow=true;if(m){m.color=new THREE.Color(0xB89B72);m.emissive=new THREE.Color(0xB89B72);m.emissiveIntensity=.38;}}\n   else if(n.startsWith('B188_')&&n.includes('PINK')){if(m){m.color=new THREE.Color(0xE0679A);m.emissive=new THREE.Color(0xE0679A);m.emissiveIntensity=.8;}}\n   else if(n.startsWith('B188_')&&n.includes('TAN')){if(m){m.color=new THREE.Color(0xB89B72);m.emissive=new THREE.Color(0xB89B72);m.emissiveIntensity=.38;}}\n   else if(n.startsWith('B188_')&&(n.includes('IRON')||n.includes('GLASS'))){if(m){m.color=new THREE.Color(0x0A0A0A);m.transparent=false;m.opacity=1;}}"),
 ("else if(n.startsWith('B167_SITE')){if(m){m.color=new THREE.Color(0x00933C);m.emissive=new THREE.Color(0x2DBE6C);m.emissiveIntensity=.75;}}",
  "else if(n.startsWith('B188_')&&n.includes('SHOPGLASS')){if(m){m.color=new THREE.Color(0x0D1714);m.transparent=false;m.opacity=1;}}"),
 ("else if(n.startsWith('B167_GLASS')){if(m)m.color=new THREE.Color(0x0D1714);}", ""),
 ("else if(n.startsWith('B167_TRIM')){if(m){m.color=new THREE.Color(0xC9C2B4);m.emissive=new THREE.Color(0xC9C2B4);m.emissiveIntensity=.25;}}", ""),
 ("else if(n.startsWith('B167_IRON')){if(m)m.color=new THREE.Color(0x0A0A0A);}", ""),
])
css = css.replace('h1 em{font-style:normal;font-weight:300;color:var(--f)}', 'h1 em{font-style:normal;font-weight:300;color:#E0679A}')   # the store is pink
body = open(os.path.join(S, 'laf_body.html')).read()
open(os.path.join(S, 'laf_template.html'), 'w').write(head + css + '</head><body>\n' + body + js)
print('template written', len(head + css + body + js) // 1024, 'KB')
