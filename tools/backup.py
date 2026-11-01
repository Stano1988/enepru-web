"""Back up content, password hash and statistics using SQLite's consistent backup API."""
import datetime,os,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
if len(sys.argv)!=2:raise SystemExit('Použití: python3 tools/backup.py /neveřejná/složka')
if not (app.DATA/'site.sqlite3').is_file():raise SystemExit('Databáze neexistuje; ověřte APP_DATA_DIR.')
destination=Path(sys.argv[1]).resolve();destination.mkdir(parents=True,exist_ok=True,mode=0o700)
name='site-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sqlite3'
p=destination/name
fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
with app.db() as source,sqlite3.connect(p) as target:source.backup(target)
print('Záloha vytvořena:',p)
