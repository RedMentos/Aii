import json
import os
from pathlib import Path
import platform
import shutil
import time
import urllib.request
from .common import APP,atomic_write,dumps,file_hash,Cancelled,Unavailable
ROLES={"C3_LANGUAGE":"language","B1_DETAIL":"body","B2_GIST":"gist","C2_CONTROL":"needle","TEACHER":"teacher"}
# Optional roles are installed only on explicit request and stay out of runtime.revisions()/event packets.
OPTIONAL_ROLES={"M_EMBED":"embedding","V_TEACHER":"vision"}  # WP-H/WP-S2 semantic memory key encoder (EmbeddingGemma)
# §85.1 G-B-TIMESCALE-DIVERGENCE-001 controls. Only 'two_body' gives B2 its own
# model; the three others are measurement controls that reuse the B1 body.
B2_CONTROLS=('two_body','shared_body_dual_state','same_model_prompt_only','same_model_same_policy')
def model_key(role,b2_control='two_body'):
    if role=='B2_GIST' and b2_control!='two_body':return 'body'
    return (ROLES|OPTIONAL_ROLES).get(role,role)
def bridge_key(models,sender,receiver,sender_tap,receiver_tap,schema_major=1,bridge_revision='none'):
    """IH-H21 BridgeKey: a latent/broadcast bridge is valid only for these exact revisions."""
    return (models.revision(sender),models.revision(receiver),sender_tap,receiver_tap,int(schema_major),str(bridge_revision))
def bridge_authority(stored_key,current_key):
    """Body swap or tap change: authority 0, shadow only, fall back to SOURCE/EXACT/CONTROL and recalibrate."""
    if stored_key is not None and tuple(stored_key)==tuple(current_key):return {'authority':'AS_CALIBRATED','fallback':None}
    return {'authority':0,'mode':'SHADOW','fallback':'SOURCE_EXACT','recalibrate':True}
def catalog():return json.loads((APP/"specs/models.json").read_text())
def platform_tag():
    machine=platform.machine().lower();arch={"aarch64":"arm64","arm64":"arm64","x86_64":"x86_64","amd64":"x86_64"}.get(machine)
    if not arch:raise Unavailable("64-bit ARM/x86 required: "+machine)
    return ("android" if os.environ.get("ANDROID_ROOT") or "com.termux" in os.environ.get("PREFIX","") else "linux")+"-"+arch
def download_file(spec,destination,progress=print,cancel=None):
    path=Path(destination);path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_file() and path.stat().st_size==spec["size"] and file_hash(path)==spec["sha256"]:return path
    partial=path.with_name(path.name+".partial")
    for attempt in range(4):
        if cancel and cancel.is_set():raise Cancelled("Download pausiert; .partial bleibt")
        size=partial.stat().st_size if partial.exists() else 0
        if size==spec["size"] and file_hash(partial)==spec["sha256"]:os.replace(partial,path);return path
        if size>=spec["size"]:partial.unlink();size=0
        if shutil.disk_usage(path.parent).free<spec["size"]-size+32*1024*1024:raise Unavailable("Zu wenig Speicher für "+path.name)
        headers={"User-Agent":"V13-Phone/0.1","Accept-Encoding":"identity"}
        if size:headers["Range"]=f"bytes={size}-"
        try:
            with urllib.request.urlopen(urllib.request.Request(spec["url"],headers=headers),timeout=30) as r:
                append=size>0 and r.status==206
                if append and not r.headers.get("Content-Range","").startswith(f"bytes {size}-"):raise ValueError("Falsche Range-Antwort")
                if not append:size=0
                previous=0
                with open(partial,"ab" if append else "wb") as f:
                    while True:
                        if cancel and cancel.is_set():raise Cancelled("Download pausiert")
                        b=r.read(512*1024)
                        if not b:break
                        f.write(b);size+=len(b)
                        if size>spec["size"]:raise ValueError("Download größer als Manifest")
                        if time.monotonic()-previous>2:progress(f"{path.name}: {size/1e6:.1f}/{spec['size']/1e6:.1f} MB");previous=time.monotonic()
                    f.flush();os.fsync(f.fileno())
            if size!=spec["size"]:raise IOError("Unvollständiger Download")
            if file_hash(partial)!=spec["sha256"]:partial.unlink();raise ValueError("SHA256 falsch, Datei verworfen")
            os.replace(partial,path);return path
        except Cancelled:raise
        except (OSError,ValueError) as e:
            progress(f"Download-Versuch {attempt+1}/4: {type(e).__name__}: {str(e)[:180]}")
            if attempt==3:raise Unavailable("Download fehlgeschlagen: "+path.name+"; :download erneut starten") from e
class ModelManager:
    def __init__(self,home,b2_control='two_body'):
        self.home=Path(home);self.b2_control=b2_control;self.router=None;self.specs=catalog();self.path=home/"config/models.json";self.installed=json.loads(self.path.read_text()) if self.path.exists() else {}
    def save(self):atomic_write(self.path,dumps(self.installed))
    def install(self,which="all",progress=print,cancel=None):
        for key in (["needle","language","body","gist"] if which=="all" else [(ROLES|OPTIONAL_ROLES).get(which,which)]):
            if key not in self.specs["models"]:raise ValueError("Modell: all|needle|language|body|gist|embedding|vision")
            s=self.specs["models"][key];progress(f"Lade {s['model_id']} · {s['license_id']}")
            files=list(s["files"])+(s["platforms"][platform_tag()] if key=="needle" else [])
            paths={}
            for f in files:
                out=self.home/"models"/key/f["local_name"];download_file(f,out,progress,cancel);paths[f["local_name"]]=str(out.relative_to(self.home))
            self.installed[key]={"model_id":s["model_id"],"exact_revision":s["revision"],"license_id":s["license_id"],"license_url":s["license_url"],"license_accepted_by_user":None,
                "download_authorization":"operator_setup_or_download","quant_format":s["quant_format"],"files":{f["local_name"]:{"path":paths[f["local_name"]],"sha256":f["sha256"],"size":f["size"]} for f in files},
                "main_file":s["main_file"],"download_complete":True,"roles":[r for r,k in (ROLES|OPTIONAL_ROLES).items() if k==key],"phone_runner_proof":None}
            self.save()
    def path_for(self,role):
        if self.router:  # WP-N11: AG0 slot route (RAMP candidate share), see bodies.BodyFabric
            p=self.router(role)
            if p:return p
        key=model_key(role,self.b2_control);s=self.installed.get(key)
        if not s or not s["download_complete"]:raise Unavailable("Modell fehlt: "+key+"; :download "+key)
        f=s["files"][s["main_file"]];p=self.home/f["path"]
        if not p.is_file() or p.stat().st_size!=f["size"]:raise Unavailable("Modell fehlt/unvollständig: "+key)
        return p
    def revision(self,role):
        rr=getattr(self,'revision_router',None)  # WP-T13: a committed online swap serves another revision
        if rr:
            v=rr(role)
            if v:return v
        return self.installed.get(model_key(role,self.b2_control),{}).get("exact_revision","unavailable")
    def verify(self,deep=False):
        results={}
        for key,s in self.installed.items():
            errors=[]
            for f in s["files"].values():
                p=self.home/f["path"]
                if not p.is_file() or p.stat().st_size!=f["size"]:errors.append(f["path"]+": missing/size")
                elif deep and file_hash(p)!=f["sha256"]:errors.append(f["path"]+": hash")
            results[key]={"ok":not errors,"hash_checked":deep,"errors":errors,"revision":s["exact_revision"]}
        return results
    def import_model(self,role,path):
        if role not in {"C3_LANGUAGE","B1_DETAIL","B2_GIST","TEACHER"}:raise ValueError("Rolle: C3_LANGUAGE/B1_DETAIL/B2_GIST/TEACHER")
        path=Path(path).expanduser().resolve()
        with open(path,"rb") as f:
            if f.read(4)!=b"GGUF":raise ValueError("Nur GGUF importierbar")
        h=file_hash(path);key=ROLES[role];dest=self.home/"models"/key/(h[:16]+".gguf");dest.parent.mkdir(parents=True,exist_ok=True)
        tmp=dest.with_suffix(".partial");shutil.copyfile(path,tmp)
        if file_hash(tmp)!=h:raise IOError("Import beschädigt")
        os.replace(tmp,dest)
        self.installed[key]={"model_id":"operator-import","exact_revision":h,"license_id":"operator-provided","license_accepted_by_user":None,"quant_format":"GGUF; inspect runner log","files":{dest.name:{"path":str(dest.relative_to(self.home)),"sha256":h,"size":dest.stat().st_size}},"main_file":dest.name,"download_complete":True,"roles":[role],"phone_runner_proof":None}
        self.save();return str(dest)
    def use_reference(self,role):
        """Explicitly reuse frozen installed weights in a separate reference lane."""
        if role not in {'B1_DETAIL','B2_GIST','C3_LANGUAGE'}:raise ValueError('Referenzrolle: B1_DETAIL|B2_GIST|C3_LANGUAGE')
        self.path_for(role)
        spec=json.loads(dumps(self.installed[ROLES[role]]));spec['roles']=['TEACHER'];spec['reference_reuse_of']=role
        self.installed['teacher']=spec;self.save();return spec
