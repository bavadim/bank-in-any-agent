#!/usr/bin/env python3
"""Rebuild PDF and offline HTML from index.html. Requires Chromium and websockets >= 12."""
import argparse
import base64
from hashlib import sha256

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.request import urlopen
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parent

PRINT = r'''(() => {
for (const details of document.querySelectorAll('[data-print-open]')) details.open=true;
return document.querySelectorAll('main > .sheet').length;
})()'''

class Browser:
    def __init__(self, proc, profile):
        self.proc=proc
        active=profile/'DevToolsActivePort'
        for _ in range(150):
            if active.exists(): break
            if proc.poll() is not None: raise RuntimeError('Chromium exited before startup')
            time.sleep(.1)
        self.port=int(active.read_text().splitlines()[0])
        with urlopen(f'http://127.0.0.1:{self.port}/json/list',timeout=5) as f:
            target=next(t for t in json.load(f) if t['type']=='page')
        self.ws=connect(target['webSocketDebuggerUrl'],max_size=32*1024*1024,open_timeout=5)
        self.seq=0

    def call(self, method, **params):
        self.seq+=1
        self.ws.send(json.dumps({'id':self.seq,'method':method,'params':params}))
        while True:
            result=json.loads(self.ws.recv(timeout=25))
            if result.get('id')!=self.seq: continue
            if 'error' in result: raise RuntimeError(result['error'])
            return result.get('result',{})

    def js(self, expression):
        result=self.call('Runtime.evaluate',expression=expression,returnByValue=True,awaitPromise=True)
        if 'exceptionDetails' in result: raise RuntimeError(result['exceptionDetails'])
        return result['result'].get('value')

    def open(self, url):
        self.call('Page.navigate',url=url)
        for _ in range(120):
            if self.js('document.readyState')=='complete' and self.js('location.href')==url: break
            time.sleep(.1)
        else: raise RuntimeError(f'Page did not finish loading: {url}')
        self.js('document.fonts.ready.then(()=>true)')


def build(browser):
    index=ROOT/'index.html'
    browser.open(index.as_uri()+'?analytics=off')
    count=browser.js(PRINT)
    browser.call('Emulation.setDeviceMetricsOverride',width=1001,height=688,deviceScaleFactor=1,mobile=False)
    browser.call('Emulation.setEmulatedMedia', media='print')
    browser.js('document.fonts.ready.then(()=>true)')
    heights=browser.js('[...document.querySelectorAll("main > .sheet")].map(e=>[e.querySelector("h1,h2").textContent,Math.round(e.getBoundingClientRect().height)])')
    pdf=base64.b64decode(browser.call('Page.printToPDF',preferCSSPageSize=True,printBackground=True)['data'])
    assert pdf.startswith(b'%PDF-') and len(pdf)>50_000
    pages=len(re.findall(rb'/Type /Page\b',pdf))
    assert pages==count,(pages,count,heights)
    (ROOT/'doomers-pitch.pdf').write_bytes(pdf)
    rev=sha256(pdf).hexdigest()[:12]
    text,n=re.subn(r'(?<=href="\./doomers-pitch\.pdf\?v=)[0-9a-f]{12}',rev,index.read_text())
    assert n==1
    index.write_text(text)
    (ROOT/'README.md').write_text(re.sub(r'PDF, \d+ страниц(?:а|ы)?',f'PDF, {pages} страниц', (ROOT/'README.md').read_text()))
    embedded=text.replace('name="pitch-format" content="website"','name="pitch-format" content="standalone"')
    for filename in ('inter-regular.woff2','inter-semibold.woff2','plex-mono.woff2','wardrobe-original.png','wardrobe-agent-concept.png'):
        mime='font/woff2' if filename.endswith('.woff2') else 'image/png'
        embedded=embedded.replace('assets/'+filename,'data:'+mime+';base64,'+base64.b64encode((ROOT/'assets'/filename).read_bytes()).decode())
    embedded=embedded.replace(f'./doomers-pitch.pdf?v={rev}','data:application/pdf;base64,'+base64.b64encode(pdf).decode())
    (ROOT/'bank-in-any-agent.html').write_text(embedded)
    print(f'PDF: {pages} pages, SHA-256 {sha256(pdf).hexdigest()}; standalone rebuilt')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--chromium',default=os.environ.get('CHROMIUM','chromium'))
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='deck-chrome-') as temp:
        profile=Path(temp)
        with (profile/'chrome.log').open('w') as log:
            process=subprocess.Popen([args.chromium,'--headless=new','--no-sandbox','--disable-dev-shm-usage','--disable-background-networking','--remote-debugging-port=0',f'--user-data-dir={temp}','about:blank'],stdout=log,stderr=log)
            try:
                browser=Browser(process,profile)
                try: build(browser)
                finally: browser.ws.close()
            finally:
                process.terminate()
                process.wait(timeout=10)

if __name__=='__main__':
    main()
