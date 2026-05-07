import os  
import re  
def scan_files():  
    pattern_form = re.compile(r'<form[^=[\"\']post[\"\'][^, re.IGNORECASE)  
    pattern_csrf = re.compile(r'{%%\s*csrf_token\s*%%}', re.IGNORECASE)  
    results = []  
    for root, dirs, files in os.walk('.'):  
        dirs[:] = [d for d in dirs if d.lower() not in ['htmlcov', 'media']]  
        for file in files:  
            if file.endswith('.html'):  
                filepath = os.path.join(root, file)  
                try:  
                    with open(filepath, 'r', encoding='utf-8') as f:  
                        content = f.read()  
                        for match in re.finditer(pattern_form, content):  
                            end_form = content.find('</form>', match.end())  
                            limit = end_form if end_form != -1 else (match.end() + 500)  
                            block = content[match.start():limit]  
                            if not pattern_csrf.search(block):  
                                line_no = content.count('\n', 0, match.start()) + 1  
                                results.append(f'{filepath}:{line_no}')  
                except: pass  
    if results:  
        for res in sorted(set(results)): print(res)  
    else:  
        print('No issues found.')  
scan_files()  
