#!/usr/bin/python3
"""Local shell orientation. Prints guidance; never changes the appliance."""
import argparse,os,shutil,textwrap
WELCOME='''
Data Ark — local knowledge, shared tools, and a Linux computer.

Source code: /opt/dataark          Library files: /mnt/storage
Tools: Python, Git, nano, GCC/make, Docker; VS Code, GHex and Codex
GitHub: https://github.com/DavJenkins/pharos
Dashboard & help: http://dataark/  Main configuration: /opt/dataark/dataark.yaml

Start here:  ark-help             Practical guide and available tools
             ark-help status      Check services, logs, storage and memory
             ark-help library     Manage content and dated reference collections
             ark-help develop     Edit, test and publish the Ark
             ark-help recovery    Backups, network changes and recovery

This is the running Ark. Routine work belongs in the admin account;
use sudo for the specific tasks that need it. Reading help changes nothing.
'''
TOPICS={
'overview':'''\
Working on the Data Ark

The Ark serves an offline library, even without an internet connection. Its
Linux computer and installed tools can also support repairs, development and
local work. The priority is to keep the shared library available.

Places to know
  /opt/dataark                 The live source-code repository (Git checkout)
  /opt/dataark/docs            Guides, architecture and handover notes
  /opt/dataark/dataark.yaml    Content catalogue and appliance configuration
  /opt/dataark/venv            Python environment for the Ark application
  /mnt/storage                Public library and portable SSD catalogue
  /var/backups/dataark         Private configuration backups; root access
  http://dataark/docs/SUMMARY.html   Local documentation in a browser

Useful admin work
  Check service health, free space, memory and recent errors.
  Add, update or remove shared content through Manage Library on the dashboard.
  Review reference editions and update sources while internet is available.
  Back up configuration before changing services or network settings.
  Edit code, run tests, keep Git checkpoints and verify published changes.
  Check the library from another device, including an offline connection.

Choose a guide: ark-help status | library | develop | recovery | basics
These guides show commands to choose from; they do not run them for you.
''',
'status':'''\
Check how the Ark is doing — these commands inspect rather than change it.

  systemctl --no-pager status dataark apache2
      Application API and web server. Press q if a pager opens.
  systemctl --failed --no-pager
      Services that need attention; an empty list is a useful result.
  journalctl -u dataark -n 50 --no-pager
      Recent API messages. Use sudo only if your account cannot read the log.
  df -h / /mnt/storage
      Free space on the system and content drive.
  free -h
      Memory and swap use. This Pi has 2 GB RAM; leave headroom for the library.
  uptime
      Running time and current load.
  ip -brief address
      Network interfaces and addresses; does not change connections.

For a fuller, read-only service/network report:
  sudo /usr/bin/python3 /opt/dataark/tools/diagnose_services.py
Review logs before sharing them; other services may include private details.
Local guide: http://dataark/docs/20-Administration/AdministratorGuide.html
''',
'library':'''\
Keep the library useful

Start in the dashboard: Settings -> System -> Manage Library.
Everyone can read public content. Shared installs/removals require the
caretaker password; that is separate from a Linux login password.

Files are under /mnt/storage and served at http://dataark/library-files/.
Use the dashboard for supported downloads and removals so readers, catalogue
entries and content files stay in step. Do not put completed forms, passwords
or private work in the public library.

Desired content configuration: /opt/dataark/config/content/content.yaml
Portable mirror: /mnt/storage/DATA-ARK-CONFIG
Preview a rebuild: /usr/bin/python3 /opt/dataark/tools/content_profile.py plan
After intentional library changes, capture a fresh profile with:
  sudo /usr/bin/python3 /opt/dataark/tools/content_profile.py export
Guide: http://dataark/docs/20-Administration/ContentRestoration.html

Reference collections have source dates and coverage notes. A stored file is
not necessarily the latest edition. Additional manually installed collections
have documented reinstall/update commands, including radio pools and callbook:
  http://dataark/docs/20-Administration/ResilienceResources.html
  http://dataark/docs/20-Administration/FamilyResources.html
  http://dataark/docs/20-Administration/Forms.html

After intentional file/catalogue changes, rebuild the portable SSD index:
  cd /opt/dataark
  sudo venv/bin/python tools/publish_content.py --help
Read the options before running a rebuild. Do not unplug the SSD during use;
shut the Ark down cleanly before moving its content drive.
''',
'develop':'''\
Develop and maintain the Ark here

Work as admin, starting in the live repository:
  cd /opt/dataark
  git status --short
  git diff

App code: app/        Browser pages/scripts: app/static/
Guides: docs/         Installers: deploy/         Maintenance tools: tools/
The API is a Python/FastAPI service; browser tools use ordinary JavaScript.
Use venv/bin/python for app dependencies. Node/npm are not installed here.

Edit in a terminal with nano, or from the graphical desktop with:
  code /opt/dataark
  ghex /path/to/a/copy-of-a-file
VS Code and GHex need a desktop session. IntelliJ (idea) is installed, but
heavy for this 2 GB Pi; keep large IDEs closed when the library needs memory.
Codex: cd /opt/dataark && codex — your own sign-in and internet are required;
installation does not provide an offline AI model.

Run the Python regression checks:
  venv/bin/python -m unittest discover -s tests

Review and commit the specific files you intended to change. The live checkout
may contain appliance-specific configuration and unrelated changes; avoid
blindly adding everything. Keep passwords and downloaded content out of Git.

Publish static pages and docs after reviewing and testing your edits:
  sudo bash deploy/deploy-web.sh
API code changes additionally need an intentional service restart:
  sudo systemctl restart dataark
Then check service status and the actual page from another device. Restarting
the API briefly interrupts its requests; editing a source file alone is not
proof that the running service or published page has changed.

Local development guide:
  http://dataark/docs/30-Developer/DevelopmentTools.html
Remote source: https://github.com/DavJenkins/pharos
''',
'recovery':'''\
Make changes recoverable

Before changing shared services or networking, record what works and capture
configuration. This backup may contain passwords; it is not a content backup:
  sudo /usr/bin/python3 /opt/dataark/tools/capture_config.py
Backups remain root-only under /var/backups/dataark. Keep another protected
copy off the Ark; a backup on the same appliance does not cover drive loss.

Keep a separate route back before changing the hotspot or upstream network.
Turning off the DataArk hotspot can disconnect the device you are using.
Do not restart networking just to inspect it. Check status and logs first.

Source/handover and recovery details:
  http://dataark/docs/20-Administration/SourceAndHandover.html
  http://dataark/docs/20-Administration/Configuration.html
  http://dataark/docs/20-Administration/AcceptanceTests.html

A tested one-script clean-image rebuild is still a goal, not an available
recovery guarantee. Preserve the source, configuration and content separately.
''',
'basics':'''\
Finding your way around the shell

  pwd                         Show your current directory
  ls                          List its files
  cd /opt/dataark             Go to the Ark source
  cd ~                        Return to your own home directory
  less docs/SUMMARY.md         Read a file; q leaves the reader
  command --help              Many commands describe their options this way
  man command                 Open an installed manual, if available
  exit                        Close this shell; this does not shut down the Ark

Tab completes file/command names. Up-arrow recalls a previous command.
Ctrl+C usually stops the current command. If an editor is open, follow its
save/exit instructions instead. A leading sudo requests administrative access
for that command; it is not needed for reading your own files or editing code
owned by admin. Use the fuller guides whenever a task is unfamiliar.

Start with ark-help status for useful checks on this appliance.
'''}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('topic',nargs='?',choices=TOPICS,default='overview');p.add_argument('--welcome',action='store_true',help='brief interactive-shell welcome');a=p.parse_args()
 if a.welcome:
  print(textwrap.dedent(WELCOME).strip())
  if os.geteuid()==0:print('\nYou are root. Use the admin account for routine source-code work.')
  return
 print(TOPICS[a.topic])
 if a.topic=='overview':
  commands=['python3','git','nano','gcc','make','docker','rsync','curl','code','ghex','java','codex']
  print('Available commands: '+', '.join(c for c in commands if shutil.which(c)))
  print('Graphical editors require a desktop session. See ark-help develop for details.')
if __name__=='__main__':main()
