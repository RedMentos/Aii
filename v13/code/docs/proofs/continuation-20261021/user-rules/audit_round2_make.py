import json,re,sys,difflib
'''Round-2 hand audit as data (decisions written by hand before the parser ran on these sentences).'''
raw=json.load(open('model_paraphrases_round2_raw.json'))
R={'B1':'B1_DETAIL','B2':'B2_GIST','C3':'C3_LANGUAGE'}
# hand decisions; anything not listed and not a copy is an error in this table
D={
(0,'B1'):(0,'owner changed (your records)'),(0,'B2'):(1,'same meaning (broader: do not touch)'),
(1,'B1'):(1,'same meaning'),(1,'B2'):(0,'garbled, no instruction'),
(2,'B1'):(1,'same meaning'),(2,'B2'):(0,'meaning changed (statement about the past)'),
(3,'B1'):(1,'same meaning (messages)'),(3,'B2'):(0,'garbled'),(3,'C3'):(0,'roles swapped (asking you)'),
(4,'B1'):(1,'same meaning'),(4,'B2'):(0,'meaning changed (ask-first dropped)'),
(5,'B1'):(1,'same meaning'),(5,'B2'):(0,'garbled'),
(6,'B1'):(1,'same meaning (that tool = the calculator)'),(6,'B2'):(0,'garbled'),
(7,'B1'):(0,'meaning changed (pay attention)'),(7,'B2'):(0,'opposite meaning (search)'),
(8,'B1'):(1,'same meaning'),(8,'B2'):(0,'meaning changed (need not)'),
(9,'B1'):(1,'same meaning'),(9,'B2'):(0,'near copy (grammar only)'),
(10,'B2'):(0,'garbled'),
(11,'B1'):(1,'same meaning'),(11,'B2'):(0,'garbled'),(11,'C3'):(1,'same meaning'),
(12,'B2'):(0,'meaning changed (do not ask too late)'),
(13,'B1'):(0,'roles swapped (the AI offers)'),(13,'B2'):(0,'garbled'),
(14,'B1'):(1,'same meaning'),(14,'B2'):(0,'roles swapped (I can write you)'),
(15,'B1'):(1,'same meaning'),
(16,'B1'):(1,'same meaning'),(16,'B2'):(1,'same meaning (ungrammatical)'),
(17,'B1'):(1,'same meaning'),(17,'B2'):(0,'garbled'),
(18,'B1'):(0,'meaning changed (delete becomes a command)'),(18,'B2'):(1,'same meaning'),
(19,'B1'):(1,'same meaning (broader: any changes)'),(19,'B2'):(0,'roles swapped'),
(20,'B1'):(1,'same meaning (broader: anything)'),(20,'B2'):(0,'garbled'),
(21,'B1'):(1,'same meaning'),(21,'B2'):(0,'garbled'),(21,'C3'):(0,'meaning changed (tell me what you need)'),
(22,'B1'):(1,'same meaning'),
(23,'B2'):(0,'garbled'),
(24,'B1'):(1,'same meaning'),(24,'B2'):(0,'meaning changed'),
(25,'B1'):(0,'meaning changed (save only the drafts)'),(25,'B2'):(0,'meaning changed (statement)'),
(26,'B1'):(1,'same meaning'),(26,'B2'):(0,'scope changed (not all files, ideas)'),
(27,'B1'):(1,'same meaning'),(27,'B2'):(1,'same meaning (never let you)'),
(28,'B1'):(1,'same meaning'),(28,'B2'):(0,'garbled'),
(29,'B1'):(1,'same meaning'),
(30,'B1'):(1,'same meaning'),
(31,'B1'):(0,'subject changed (I should not)'),(31,'B2'):(1,'same meaning'),
(32,'B1'):(0,'owner changed (your entries)'),(32,'B2'):(1,'same meaning'),
(33,'B2'):(0,'garbled'),(33,'C3'):(0,'content added (no connection yet)'),
(34,'B2'):(0,'roles swapped (I am ready to install)'),
(36,'B1'):(0,'statement (no uploads happening)'),(36,'B2'):(1,'same meaning'),
(37,'B1'):(1,'same meaning'),(37,'B2'):(0,'garbled'),(37,'C3'):(1,'same meaning'),
(38,'B1'):(0,'meaning changed (share instead of remember)'),
(39,'B1'):(1,'same meaning'),(39,'B2'):(0,'garbled'),
(40,'B1'):(0,'roles swapped (your permission)'),(40,'B2'):(1,'same meaning'),
(41,'B1'):(1,'same meaning'),(41,'B2'):(0,'garbled'),
(42,'B1'):(1,'same meaning'),(42,'B2'):(1,'same meaning (ungrammatical)'),
(43,'B1'):(1,'same meaning'),
(44,'B1'):(1,'same meaning (phone numbers or addresses)'),(44,'B2'):(0,'meaning changed'),(44,'C3'):(0,'near copy (circumstance)'),
(45,'B1'):(1,'same meaning'),(45,'B2'):(0,'garbled'),(45,'C3'):(0,'scope changed (on that)'),
(46,'B1'):(1,'same meaning (anyone, scripts)'),(46,'B2'):(1,'same meaning (past tense prohibition)'),
(47,'B1'):(1,'same meaning'),(47,'B2'):(0,'scope changed (not everything)'),
(48,'B1'):(0,'meaning changed (forbid becomes ask-first)'),(48,'B2'):(0,'statement of intent, not an instruction'),(48,'C3'):(1,'same meaning'),
(49,'B1'):(0,'roles swapped (when you let me know)'),(49,'B2'):(0,'roles swapped (I must change)'),(49,'C3'):(0,'near copy (grammar only)'),
(50,'B1'):(1,'same meaning'),(50,'B2'):(0,'garbled'),
(51,'B1'):(1,'same meaning'),(51,'B2'):(1,'same meaning'),
(52,'B1'):(1,'same meaning'),(52,'B2'):(0,'near copy (lösche)'),
(53,'B2'):(1,'same meaning (ungrammatical)'),
(54,'C3'):(1,'same meaning'),
(55,'B1'):(1,'same meaning'),(55,'B2'):(1,'same meaning (ungrammatical)'),
(56,'B1'):(1,'same meaning'),(56,'B2'):(1,'same meaning'),(56,'C3'):(0,'meaning changed (question)'),
(57,'B1'):(1,'same meaning'),(57,'B2'):(0,'statement of intent, not an instruction'),
(58,'B1'):(1,'same meaning (impersonal)'),
}
n=lambda s:re.sub(r'[^\w]+',' ',s.lower()).strip()
rows=[];used=set()
for r in raw['rows']:
    k=(r['index'],r['role'][:2]);s=r['sentence'] or ''
    ratio=difflib.SequenceMatcher(None,n(s),n(r['original'])).ratio()
    if n(s)==n(r['original']):acc,why=0,'COPY'
    elif ratio>=0.85 and k not in D:acc,why=0,'near copy (ratio %.2f)'%ratio
    else:
        if k not in D:sys.exit('no decision for %r %r'%(k,s))
        acc,why=D[k];used.add(k)
    rows.append({'index':r['index'],'role':r['role'],'sentence':s,'accepted':bool(acc),'reason':why})
assert used==set(D),set(D)-used
json.dump({'schema':'USER_RULES_PARAPHRASE_AUDIT_V1','round':2,
 'rule':'hand audit before the parser ran on these sentences: accept only if the rewrite keeps the meaning (language may change); identical copies (ignoring case and punctuation) and near copies are excluded; labels are inherited from the holdout item unchanged',
 'rows':rows},open('audit_round2.json','w'),ensure_ascii=False,indent=1)
hold={i:it for i,it in enumerate(json.load(open('holdout_author.json'))['items'])}
items=[]
for r in rows:
    if r['accepted']:
        h=hold[r['index']];items.append(dict({k:v for k,v in h.items() if k!='text'},text=r['sentence'],source=r['role'],original=h['text']))
json.dump({'schema':'USER_RULES_MODEL_COHORT_V1','round':2,'items':items},open('model_cohort_round2.json','w'),ensure_ascii=False,indent=1)
import collections;print(len(items),collections.Counter(r['reason'] for r in rows if not r['accepted'])['COPY'],collections.Counter(r['role'] for r in rows if r['accepted']))
