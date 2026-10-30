#!/usr/bin/env python3
"""Render the public gap register from its reviewed, human-editable JSON assessment."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def render(data):
 entries=data['unavailable_entries'];missing=[x for x in entries if x.get('disposition') not in ('retired','optional')];deferred=[x for x in entries if x.get('disposition') in ('retired','optional')];omitted=data['omitted_candidates'];resolved=data.get('resolved_entries',[])
 lines=['# Content download gaps and alternatives','',
        'Updated '+data.get('updated_at',data['audited_at'])[:10]+'. This register separates unavailable documents, useful alternatives and actual uncovered needs. It is not a list of proposed new collections.','',
        str(len(missing))+' unavailable catalogue entries; '+str(len(omitted))+' omitted candidates; '+str(len(resolved))+' entries resolved or corrected. Related guides do not mean the requested document is installed. HTTP errors describe recorded requests, not whether you can open a public document in your browser.','',
        '## How to read this report','',
        'This is an acquisition and coverage register, not the Ark’s live health report. Historical unavailable sources and subject gaps can remain here while the Ark has no active warnings. Resolved entries below identify saved copies or explicitly described replacements; they do not prove complete subject coverage. [Current capture and browser-review queue](/capture.html).','',
        '[Capture missing PDFs or review updates](/capture.html). Successful captures automatically move their entry to the resolved section. The capture page also shows current update-check status.','',
        '## Recorded acquisition and coverage gaps','']
 for folder in dict.fromkeys(x['collection'] for x in missing):
  lines+=['### '+folder,'']
  for x in missing:
   if x['collection']!=folder:continue
   lines+=['['+x['title']+']('+x['source_url']+')','',
           '- Recorded failure: '+x['observed_failure']+' (last attempt '+x['last_attempt'][:10]+').',
           '- Coverage: '+x['assessment']+'. '+x['installed_alternative'],
           '- Decision: '+x['retry_priority'],'']
 lines+=['## Optional and retired references','']
 for x in deferred:
  lines+=['### '+x['title'],'',x['disposition'].capitalize()+'. '+x['retry_priority'],'','- Original source: '+x['source_url'],'- Recorded failure: '+x['observed_failure'],'- Alternative: '+x['installed_alternative'],'']
 lines+=['## Resolved entries and corrected targets','']
 for x in resolved:
  title='['+x['title']+']('+x['local_url']+')' if x.get('local_url') else x['title']
  lines+=[title,'',x['resolution']+((' '+str(x['pages'])+' PDF pages.') if x.get('pages') else ''),'']
  if x.get('evidence_url'):lines+=['[Publisher evidence]('+x['evidence_url']+')','']
 lines+=['## Candidates omitted before registration','', 'These are separate from the current unavailable count. Exact URLs were not retained for two early candidates; no replacement URL has been invented.','']
 for x in omitted:
  title='['+x['title']+']('+x['url']+')' if x.get('url') else x['title']
  lines+=[title,'','- Recorded failure: '+x['reason']+'.', '- Alternative: '+x['alternative'], '- Decision: '+x['priority'], '[Original record]('+x['evidence']+')','']
 lines+=['## Remaining scope and maintenance limits','',
         'Not every blocked URL represents a distinct uncovered need. The installed NCAT hydro guide addresses dedicated hydro planning differently from the failed DOE/Colorado titles. Public state amendments do not include the complete copyrighted ICC/NFPA base books. Gardner ordinance text and small-claims procedure remain separate gaps. Owner manuals are not full Honda factory workshop manuals. Pregnancy-specific coverage and screen-reader/easy-read equivalence remain unverified.','',
         'The 2025 Title 44 volume-2 target was erroneous: the [official GovInfo directory](https://www.govinfo.gov/bulkdata/CFR/2025/title-44) lists volume 1 only, already installed. Annual snapshots are not live eCFR. Legal and technical currency must be checked against the actual jurisdiction and edition.','',
         'Earlier failures resolved by other sources include the ACS bleeding booklet (Indiana DHS), mold originals (EPA/Winnebago/Global Handwashing Partnership), water guidance (EPA), winter references (NWS/archived FEMA/Texas A&M) and the correct AVMA 2023 pet brochure. These are explained in their collection maintenance guides.','',
         'Publisher checks for captured PDFs are manual. A failed check does not remove or invalidate an installed copy. Browser comparisons resolve unknown checks; different verified bytes require explicit replacement with the current baseline hash. Previous verified copies are retained privately on the system disk. Pinned tax years cannot silently advance. [Browser capture and update guide](BrowserCapture.md).','',
         'The editable assessment is deploy/reference/content-gaps.json in /opt/dataark and the [GitHub source](https://github.com/DavJenkins/pharos/blob/feature/readme-foundation/deploy/reference/content-gaps.json). Collection sources.json files retain installed provenance and hashes. tools/build_content_gap_report.py renders this page after an import. Exact document equivalence and complete subject coverage are not inferred from a successful download.']
 return '\n'.join(lines)+'\n'

def main():
 data=json.loads((ROOT/'deploy/reference/content-gaps.json').read_text(encoding='utf-8'))
 (ROOT/'docs/20-Administration/ContentGaps.md').write_text(render(data),encoding='utf-8')
if __name__=='__main__':main()
