#!/usr/bin/env python3
"""Only refresh the two approved header CSS URLs; retain all other bytes."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
VERSION='20261017-controls22'
def refresh(text):
    return re.sub(r'((?:section-navigation|search-entry)\.css)\?[^"\s]+',lambda m:m[1]+'?v='+VERSION,text)
def main():
    count=0
    for p in (ROOT/'docs').rglob('*.html'):
        old=p.read_text();new=refresh(old)
        if old!=new:p.write_text(new);count+=1
    print('Header CSS version refreshed:',count,'pages')
if __name__=='__main__':main()
