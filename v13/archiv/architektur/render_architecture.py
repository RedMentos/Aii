from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from html import escape
import math, json, hashlib, textwrap, zipfile

ROOT=Path('/workspace/scratch/34271631152d')
SRC=ROOT/'audit/V13-Redmi-Start/V13-Phone'
OUT=ROOT/'output'
W,H=2400,3700
BG='#F5F7FB'; INK='#14243B'; MUTED='#53657D'; LINE='#BCC8D6'
COL={'DA':'#147856','TEIL':'#A76A0C','LAB':'#7150AA','PLAN':'#667487'}
FILL={'DA':'#EDF8F3','TEIL':'#FFF8E9','LAB':'#F3EFFA','PLAN':'#F0F3F7'}
im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im);svg=[]
fontdir=Path('/usr/share/fonts/truetype/dejavu')
fonts={}
def font(size,bold=False):
    k=(size,bold)
    if k not in fonts: fonts[k]=ImageFont.truetype(str(fontdir/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')),size)
    return fonts[k]
def rect(x,y,w,h,fill='#FFFFFF',stroke=LINE,r=14,width=2,dash=False):
    d.rounded_rectangle((x,y,x+w,y+h),radius=r,fill=fill,outline=stroke,width=width)
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"'+(' stroke-dasharray="10 8"' if dash else '')+'/>')
def txt(x,y,s,size=28,color=INK,bold=False):
    d.text((x,y),s,font=font(size,bold),fill=color)
    svg.append(f'<text x="{x}" y="{y+size*.94}" font-family="DejaVu Sans, sans-serif" font-size="{size}" font-weight="'+('700' if bold else '400')+f'" fill="{color}">{escape(s)}</text>')
def line(points,color=LINE,width=3,dash=False,arrow=False):
    if dash:
        for a,b in zip(points,points[1:]):
            le=math.dist(a,b)
            for s in range(0,int(le),18):
                e=min(s+10,le);d.line([(a[0]+(b[0]-a[0])*t/le,a[1]+(b[1]-a[1])*t/le) for t in (s,e)],fill=color,width=width)
    else:d.line(points,fill=color,width=width,joint='curve')
    svg.append('<polyline points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="{width}"'+(' stroke-dasharray="10 8"' if dash else '')+'/>')
    if arrow:
        a,b=points[-2:];an=math.atan2(b[1]-a[1],b[0]-a[0]);pts=[b,(b[0]-17*math.cos(an-.45),b[1]-17*math.sin(an-.45)),(b[0]-17*math.cos(an+.45),b[1]-17*math.sin(an+.45))]
        d.polygon(pts,fill=color);svg.append('<polygon points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in pts)+f'" fill="{color}"/>')
def pill(x,y,status):
    ww={'DA':67,'TEIL':91,'LAB':82,'PLAN':104}[status]
    rect(x,y,ww,38,FILL[status],COL[status],r=8,width=1)
    txt(x+12,y+4,status,23,COL[status],True)
def box(x,y,w,h,title,lines,status='TEIL',size=27):
    rect(x,y,w,h,FILL[status],COL[status],width=2,dash=status=='PLAN')
    txt(x+24,y+17,title,30,INK,True)
    # Status appears in its own reserved line so long titles stay readable.
    pill(x+24,y+62,status)
    for i,s in enumerate(lines):txt(x+24,y+112+i*39,s,size,MUTED)
def panel(y,h,tag,title,sub):
    rect(82,y,2236,h,'#FFFFFF',LINE,r=18)
    txt(110,y+18,tag,31,COL['LAB'],True)
    txt(110+int(d.textlength(tag,font=font(31,True)))+32,y+18,title,34,INK,True)
    txt(110,y+68,sub,27,MUTED)

txt(82,46,'V13 / INQUISITION',60,INK,True)
txt(82,124,'Architektur aus Code, erhaltenen Nachweisen und Canon',33,MUTED)
txt(82,174,'Gesicherter Stand: 09.10.2026 · 00:28 CEST  |  Age 0 · Text  |  WORK IN PROGRESS',27,MUTED)
for x,st,label in [(82,'DA','Im angegebenen Umfang vorhanden'),(720,'TEIL','Teilpfad vorhanden; Gesamtziel offen'),(1440,'LAB','Isolierter Versuch'),(1920,'PLAN','Geplant / gesperrt')]:
    pill(x,222,st);txt(x+({'DA':82,'TEIL':108,'LAB':99,'PLAN':120}[st]),226,label,24,MUTED)

panel(290,355,'A-PLANE','Eingang / Wahrnehmung','Aktiv: exakter Text und Quellenbindung. Bild, Audio und Sensorports sind noch nicht angeschlossen.')
box(110,404,680,205,'A0 / A1 · Rohquelle + Segmente',['UTF-8-Quelle → stabile Textspans','A0: Text da; weitere Modalitäten offen'],'TEIL')
box(820,404,780,205,'A2 / A3 · Referenz + Student',['Frozen Needle-Targets → 16D-Textstudent','Alignment + Rekonstruktion; JEF-SHADOW'],'TEIL')
box(1630,404,660,205,'A4 / A5 · PerceptPacket',['A4: begrenzte Views; Salienz offen','A5: exakte SourceRef + Hash da'],'TEIL')
line([(450,645),(450,712)],COL['DA'],4,arrow=True)
txt(480,663,'fine-view: 240 Zeichen',25,MUTED)
line([(1950,645),(1950,712)],COL['DA'],4,arrow=True)
txt(1470,663,'gist-view: 960 Zeichen',25,MUTED)

panel(714,607,'B-PLANE','Split-Brain-Core','Zwei Rollen und getrennte Zustände; aktuell dieselben eingefrorenen LFM2.5-1.2B-Q4-Gewichte.')
box(110,831,680,278,'B1 · DETAIL / fein',['Wortlaut, Zahlen, Code; kurzer Zustand','Native JSON-Angebote + Quellenzitate','Kann selbst die finale Antwort erzeugen','Read-only 2048D-Tap + Zusatzpredictor'],'TEIL')
box(820,831,780,278,'B3 · Callosum / Nachrichten',['NO_MESSAGE / SOURCE_EXACT','CONTROL / SYMBOLIC; Quellen geprüft','B1 → B2, optional ein B1-Re-entry','Gelernte latente Bridge: OFF'],'TEIL')
box(1630,831,660,278,'B2 · GIST / grob',['Ziele, Kontext, Zusammenfassung','Bis 4 alte Angebote; 768 Kontextzeichen','Quellengebunden, Neustart-isoliert','Gleicher Body; keine MoE-Trennung'],'TEIL')
line([(790,943),(820,943)],COL['DA'],4,arrow=True)
line([(1600,943),(1630,943)],COL['DA'],4,arrow=True)
line([(1630,1043),(1615,1043),(1615,1130),(808,1130),(808,1043),(790,1043)],COL['DA'],3,arrow=True)
txt(1130,1124,'höchstens 1 Rückfrage',23,MUTED)
rect(110,1182,2180,104,'#F5F7FB',LINE)
txt(132,1195,'B4 · Workspace: explizite frische Angebote     B5 · Memory / Self / World-Schnittstellen',29,INK,True)
txt(132,1239,'Persistierter Quellenkontext ist vorhanden; dauerhafter gemeinsamer nativer KV-State ist nicht belegt.',26,MUTED)
line([(1200,1321),(1200,1391)],COL['DA'],4,arrow=True)
txt(1230,1328,'Angebote / Evidenz / Unsicherheit',26,MUTED)
# Non-serial topology: source can enter JEF directly, and JEF queries bodies.
line([(110,627),(52,627),(52,1460),(110,1460)],COL['DA'],4,arrow=True)
txt(82,1353,'Direktpfad A → JEF',24,COL['DA'],True)
line([(2180,1401),(2350,1401),(2350,770),(2300,770)],COL['LAB'],3,arrow=True)
txt(1660,1365,'JEF → B: Query / Broadcast / Re-entry',24,COL['LAB'])

panel(1394,648,'C-PLANE','JEF = Executive + Control + Sprache + Report','JEF kann ohne B arbeiten. Modelle liefern Inhalte; C5 besitzt die lokale Ausgabeautorität.')
box(110,1512,515,196,'C0 / C1 · Shell + Executive',['Operator, Ziel, Constraints, Zustand','Source-Governor + Broadcast'],'TEIL',25)
box(655,1512,520,196,'C2 · CONTROL / Needle3',['~35 MB CQ2; strukturierte Routen','Scaffold + freigegebene Heads'],'TEIL',25)
box(1205,1512,540,196,'C4 · Fokale Auswahl',['Frische Angebote; Wake / Halt','Begrenzte Koalition + 1 Re-entry'],'TEIL',25)
box(1775,1512,515,196,'C3 · LANGUAGE',['LFM2.5-230M Q4 · ~149 MB','Freie Sprache + First-Token-Delta'],'TEIL',25)
line([(625,1609),(655,1609)],COL['DA'],3,arrow=True)
line([(1175,1609),(1205,1609)],COL['DA'],3,arrow=True)
line([(1745,1609),(1775,1609)],COL['DA'],3,arrow=True)
box(110,1750,1065,190,'C5 · ActionIntent / Corollary / Report-Broker',['Freigegebene exakte Regeln + Copy-Pfad ohne Modell','Native Finalroute: simple → C3; detail/both → B1; gist → B2'],'DA',25)
box(1205,1750,1085,190,'C6 / C7 · Ausgabe / Effectors',['TTY-Chat, Streaming, gespeicherte Antwort + ActionOutcome','Geplant: Sprache, Bild, App-Klicks, weitere externe Aktionen'],'TEIL',25)
line([(2030,1708),(2030,1730),(800,1730),(800,1750)],COL['DA'],3,arrow=True)
line([(1175,1845),(1205,1845)],COL['DA'],4,arrow=True)
txt(110,1980,'Schneller Regelpfad: exakte freigegebene Antwort → C5 → TTY. Kein allgemeiner neuronaler Antwortprüfer.',26,MUTED)

panel(2090,603,'FABRICS','Quersysteme für A, B und JEF','Gemeinsame Dienste mit eigenen Quellen, Zuständen und Freigaben; keine zusätzlichen Hemisphären.')
frows=[
('F1 · Attention / Admission','Freshness + Source-Gates; gelernter Gain offen','TEIL'),
('F2 · Interrupt / Reflex','Cancel, Preemption, Ressourcengrenzen','TEIL'),
('F3 · Memory / Provenance','Exact + Episodic + gelernte Paar-Relevanz','TEIL'),
('F4 · Self / World / Fast Forward','Digitale Outcomes, Timing + Latent-Prognose','TEIL'),
('F5 · Action / Safety / Corollary','Lokaler Text-Aktionszyklus; externe Wahl offen','TEIL'),
('F6 · Learning / Eligibility','10 getrennte Zusatzkomponenten; Basis frozen','TEIL'),
('F7 · Homeostasis / Stability','Gemessene Budget-/Norm-Regelung; neural offen','TEIL'),
('F8 · Human / Age / Rules','Freigabe, Generation, Widerruf, Rollback; Age 0','DA'),
('F9 · Replay / Dream / Consolidation','Replay + bestätigte Indizes; keine Weight-Merge','TEIL'),
('F10 · Runtime / Cache / Governor','SQLite-WAL, Queue, RSS/PSS; Phone-Proof offen','TEIL'),
('F11 · Metrics / Calibration / Retention','Tests + Ablationen; OOD/Gesamtnutzen offen','TEIL'),
('Persistenter Unterbau','Chats, Quellenblobs, Experience, Backup, Export','DA')]
for i,(title,sub,st) in enumerate(frows):
    x=110+(i%3)*738;y=2210+(i//3)*113
    rect(x,y,704,98,FILL[st],COL[st],r=10)
    sz=27
    while d.textlength(title,font=font(sz,True))>592:sz-=1
    txt(x+16,y+12,title,sz,INK,True);txt(x+16,y+55,sub,22,MUTED)
    txt(x+622,y+16,st,20,COL[st],True)

panel(2741,377,'LERNEN','Was tatsächlich trainierbare Zusatzpfade hat','Quellen/Labels → expliziter SHADOW-Job → Evaluation/Retention → einzelne Freigabe → Neustart / Rollback.')
learn=[('C2 Route','4 Klassen · Needle frozen'),('C2 Wake','none / detail / gist / both'),('C2 Halt','halt / continue'),('C2 Kalibrierung','Native Route-Agreement'),('C3 Output-Delta','Nur erster nativer Token'),('A3 Textstudent','512D Raw → 16D Latent'),('B1 Predictor','2048D Tap → t+2'),('B2 Predictor','2048D Tap → t+2'),('World Predictor','Digitale Aktion → Outcome'),('Memory Relevance','Needle Query/Source-Paar')]
for i,(title,sub) in enumerate(learn):
    x=110+(i%5)*440;y=2863+(i//5)*98
    rect(x,y,414,81,FILL['TEIL'],COL['TEIL'],r=9)
    txt(x+14,y+9,title,26,INK,True);txt(x+14,y+46,sub,21,MUTED)
txt(110,3080,'EMA: lokale Body-/World-Predictors. Kein freigegebenes Basismodell-Training; RECORD_ONLY lernt nicht.',24,MUTED)

box(82,3164,1090,338,'LAB · Neue native Schnittstellen',['Same-prefill Observer: 5/5 Paare invariant','Pause / Resume: gleicher Prozess und Kontext','Final-norm Receiver: numerischer Effekt gemessen','Norm-Training: Utility-Gates verwerfen Kandidaten','Mid-layer: kompiliert + 32 Guards; Effekt noch offen','Keine B3- oder Produktionsfreigabe daraus'],'LAB',25)
box(1208,3164,1110,338,'PLAN · Noch zu bauen / zu beweisen',['Sparse/MoE-Bodies + aktive Gewichts-/Quant-Deltas','Body-/Cross-/Executive-JEPA + gelernte B3-Bridge','Breite Inquisition, Skill-/Semantik-Weight-Konsolidierung','Native KV-Kontinuität, günstiger residenter Phone-Pfad','Vision/Audio, Full-Duplex, Tools/Apps, höhere Ages','Teacher-Removal erst nach stabilen Nachweisen'],'PLAN',25)
txt(82,3542,'OFFENE GATES',27,INK,True)
txt(365,3542,'STEP2: 42/70 neue Zeilen strukturell geprüft; semantische Komplementarität nicht belegt.',26,MUTED)
txt(82,3590,'C3-Retrieval: 27/28, Quellenwert-Consumer scheitert. Aktueller Redmi-Dauerlauf / Thermal / Energie / KV fehlen.',26,MUTED)
txt(82,3650,'Audit: Runtime + Worker + native C++ + Canon + erhaltene Proofs. Grün gilt nur im beschrifteten Umfang; kein Live-Zugriff auf den anderen Chat.',22,MUTED)

png=OUT/'V13-Architektur-20261009.png';im.save(png)
sv=OUT/'V13-Architektur-20261009.svg'
sv.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><title>V13 Inquisition Architektur, gesicherter Stand 9. Oktober 2026</title><desc>Alle 30 Canon-Komponenten, zehn externe Lernpfade, native Experimente und noch gesperrte Ziele; Code- und Evidenz-Audit des Rettungsarchivs.</desc><rect width="{W}" height="{H}" fill="{BG}"/>'+''.join(svg)+'</svg>')
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
c=canvas.Canvas(str(OUT/'V13-Architektur-20261009.pdf'),pagesize=(W/2,H/2));c.setTitle('V13 / Inquisition — Code Architecture Audit');c.drawImage(ImageReader(im),0,0,W/2,H/2);c.save()

print(json.dumps({'png':str(png),'svg':str(sv),'size':[W,H]},ensure_ascii=False))
