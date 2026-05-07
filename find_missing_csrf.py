@echo off  
import os, re  
def scan_files():  
    p_f = re.compile(r'<form[^=[\"\']post[\"\'][^, re.I)  
    p_c = re.compile(r'{%%\s*csrf_token\s*%%}', re.I)  
    res = []  
    for r, ds, fs in os.walk('.'):  
        ds[:] = [d for d in ds if d.lower() not in ['htmlcov', 'media']]  
        for f in fs:  
            if f.endswith('.html'):  
                path = os.path.join(r, f)  
                try:  
                    with open(path, 'r', encoding='utf-8', errors='ignore') as fh:  
                        txt = fh.read()  
                        for m in p_f.finditer(txt):  
                            end = txt.find('</form>', m.end())  
                            blk = txt[m.start():(end if end != -1 else m.end()+500)]  
                            if not p_c.search(blk): res.append(f'{path}:{txt.count(\"\n\", 0, m.start())+1}')  
                except: pass  
    for x in sorted(set(res)): print(x)  
scan_files()  
