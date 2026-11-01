"""WP-FS3/FS4 CLI: meta_i report for [[confidence, correct], ...] JSON files (e.g. DS3b captures), ECE next to it.
Usage: python scripts/metaeff_report.py pairs.json [more.json ...]"""
import json,os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
from v13.agi import metaeff
from v13.agi.generality import calibration
for f in sys.argv[1:]:
    pairs=[tuple(x) for x in json.load(open(f))];r=metaeff.report(pairs)
    print(json.dumps({'file':os.path.basename(f),'ece':calibration(pairs)['ece'],'meta':r,'abstain':metaeff.abstain_utility(pairs)}))
