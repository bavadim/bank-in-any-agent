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
const get = id => document.getElementById(id);
const escape = value => { const p=document.createElement('span'); p.textContent=value; return p.innerHTML; };
const section = (label, title, body) => `<section class="sheet"><p class="print-label">${label}</p><h2>${title}</h2>${body}</section>`;
const content = sel => document.querySelector(sel).outerHTML;
const keys = ['calculator', 'team'];
const panels = {};
for (const key of keys) {
  document.querySelector(`[data-source="${key}"]`).click();
  panels[key] = get('evidence-body').innerHTML;
  get('evidence-dialog').close();
}
const hero = get('thesis').cloneNode(true); hero.querySelector('.thesis-note').remove();
const mechanism = get('mechanism').querySelector('.wrap').cloneNode(true);
mechanism.querySelector('.trigger-v2 a').remove();
const risk = [...document.querySelectorAll('.risk-item')].map(el => {
  const clone = el.cloneNode(true); clone.querySelector('details').open=true; return clone.outerHTML;
});
const calc = [...get('scale').querySelectorAll('input')].map(i=>{
  const control=i.closest('.control');
  return `<li><b>${i.labels[0].textContent}:</b> ${escape(control.querySelector('output').textContent)}<br>${escape(control.querySelector('.funnel-result').textContent)}<br><small>${escape(control.querySelector('.funnel-caption').textContent)}</small></li>`;
}).join('');
const settings = [...document.querySelectorAll('#product-settings input,#roi-settings input')].map(i=>`<li>${escape(i.labels[0].textContent)}: <b>${escape(i.value)}</b></li>`).join('');
const method = document.createElement('div'); method.innerHTML=panels.calculator;
const methodParts=[...method.children].map(e=>e.outerHTML);
const links = [...document.querySelectorAll('.source-list li')].map(e=>e.outerHTML);
const caseBody = `<div class="print-case"><img src="${get('original-screenshot').getAttribute('src')}" alt="Исходный скриншот"><div>${document.querySelector('#case .section-lead').outerHTML}${content('.case-copy')}</div></div>`;
const team=get('team').querySelector('.team-grid').outerHTML;
const wrap = body => `<div class="paper">${body}</div>`;
const results = content('#scale .results');
document.body.innerHTML = [
 wrap(hero.innerHTML),
 wrap([...mechanism.children].slice(0,3).map(e=>e.outerHTML).join('')),
 section('01 / Общий механизм', 'От полезного скилла к первому взносу', mechanism.querySelector('.funnel-steps').outerHTML+mechanism.querySelector('.trigger-v2').outerHTML),
 section('02 / Пример', 'Банковский скилл продолжает подбор одежды', caseBody),
 section('03 / Экономика привлечения', 'Аудитория маркетплейса. Доход банка.', content('#scale .section-lead')+`<div class="print-economy"><ul>${calc}</ul>${results}</div>`),
 section('03 / Расчёт', 'Параметры сценария', `<ul class="print-settings">${settings}</ul>`+methodParts.slice(0,4).join('')),
 section('03 / Расчёт', 'Доход, расходы и окупаемость', methodParts.slice(4).join('')),
 section('04 / Риски', 'Ставка большая. Проверка начинается с малого.', content('.risk-scope')+`<div class="print-risk">${risk.slice(0,2).join('')}</div>`),
 section('04 / Риски', 'Критические предпосылки канала', `<div class="print-risk">${risk.slice(2,4).join('')}</div>`),
 section('04 / Эксперимент', 'Две недели на первые сигналы', `<div class="print-risk">${risk[4]}${content('.pilot')}</div>`),
 section('05 / Команда', 'От MCP — к живому сценарию.', team+panels.team+`<p>Обратная связь: ${get('feedback-email').outerHTML}</p>`),
 section('Источники', 'Данные и исследования', `<ol class="print-sources">${links.slice(0,6).join('')}</ol>`),
 section('Источники', 'Тарифы и допущения', `<ol class="print-sources">${links.slice(6).join('')}</ol>`),
].join('');
const css=document.createElement('style');css.textContent=`
@page{size:A4 landscape;margin:10mm 16mm}
body{font-size:14px;background:#fff;color:#18191b;color-scheme:light;--muted:#45484c;--white:#18191b;--lime:#354e0d;--lilac:#4a3975;--line:#cfcec7}
body .paper,body .sheet{break-before:page; padding:0; width:auto; margin:0;break-inside:auto;zoom:.94}body .paper{zoom:.81}body .paper:first-child{break-before:auto}
.print-label,.section-label,.eyebrow{font:12px Plex,monospace;text-transform:uppercase;color:#45484c;margin:0 0 12px}
.paper h1{font-size:44px;line-height:1.05;letter-spacing:-.05em;margin:0 0 14px}.paper h1 em{font-style:normal;color:#354e0d}
.sheet>h2,.paper>h2{font-size:34px;line-height:1.08;letter-spacing:-.045em;margin:0 0 22px}
.sheet h3,.paper h3{font-size:18px}.sheet p,.paper p,.sheet li{font-size:14px;line-height:1.5}
.thesis-grid-v2{margin-top:22px}.thesis-card-v2,.thesis-card-v2:nth-child(even){padding:16px 18px}.thesis-card-v2 h2{font-size:24px;margin-bottom:10px}.thesis-meta-v2{margin-bottom:10px}.thesis-card-v2>p,.thesis-card-v2 .thesis-proof-v2{font-size:13px;margin-bottom:9px}.status,.status.hyp{color:#354e0d}.hero-subtitle-v2 b{color:#18191b}#hero-revenue-value{color:#354e0d}
.value-pair{margin-top:18px}.value-pair article{padding-block:14px}.funnel-heading{margin-top:18px}.journey-v2.funnel-steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px 25px}.funnel-steps li{padding:10px 0;border:0}.funnel-steps li .mono{position:static}.funnel-steps h3{margin:5px 0;font-size:18px}.funnel-steps p{margin:0}.trigger-v2{margin-top:15px}
.sheet a,.paper a,.thesis-links-v2 a{color:#354e0d;text-decoration:underline}.sheet button,.paper button,.screen-hint{display:none!important}
.print-case{display:grid;grid-template-columns:240px 1fr;gap:34px}.print-case>img{width:100%;height:525px;object-fit:contain;object-position:top}.print-case .case-copy p{font-size:14px}.print-case .agent-reply{max-width:none}.print-case .section-lead{margin-top:0}
.print-economy,.print-risk{display:grid;grid-template-columns:1fr 1fr;gap:35px;align-items:start}.print-economy ul,.print-settings,.print-sources{padding-left:22px}.print-economy li,.print-settings li,.print-sources li{margin-bottom:10px}.print-settings{columns:2}.print-economy .results{display:block;padding:0}.result-number{font-size:54px}.result-split{padding:12px 0}.result-split strong{font-size:27px}.roi-card{padding:12px}.roi-heading{margin-bottom:10px}.roi-grid{gap:10px}.roi-grid strong{font-size:22px}
.print-risk .risk-item{border-top:1px solid #ccc;border-bottom:0;padding:15px 0;break-inside:avoid}.print-risk .risk-evidence summary{color:#4a3975}.print-risk .pilot{padding:15px 0}.pilot .big-nine{color:#354e0d;font-size:60px}.team-grid{display:grid;gap:30px}.team-grid h2{display:none}.team-arguments>div{padding:6px 0}.team-arguments h3{margin:4px 0}.team-arguments p{margin:4px 0}
`;document.head.append(css);
return document.querySelectorAll('.paper,.sheet').length;
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
    heights=browser.js('[...document.body.children].map(e=>[e.querySelector("h1,h2").textContent,Math.round(e.getBoundingClientRect().height)])')
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
