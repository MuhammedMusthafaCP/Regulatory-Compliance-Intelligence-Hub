"""Minimal tolerant HTML tree builder (stdlib only).

EUR-Lex pages are XHTML with unclosed <meta> tags, so strict XML parsers fail.
"""
from html.parser import HTMLParser
VOID={'meta','link','br','col','img','hr','input'}
class Node:
    __slots__=('tag','attrs','children','parent')
    def __init__(s,tag,attrs,parent): s.tag=tag;s.attrs=dict(attrs);s.children=[];s.parent=parent
    def get(s,k): return s.attrs.get(k)
    def iter(s):
        yield s
        for c in s.children:
            if isinstance(c,Node): yield from c.iter()
class B(HTMLParser):
    def __init__(s): super().__init__(convert_charrefs=True); s.root=Node('root',[],None); s.cur=s.root
    def handle_starttag(s,t,a):
        n=Node(t,a,s.cur); s.cur.children.append(n)
        if t not in VOID: s.cur=n
    def handle_startendtag(s,t,a): s.cur.children.append(Node(t,a,s.cur))
    def handle_endtag(s,t):
        n=s.cur
        while n is not s.root and n.tag!=t: n=n.parent
        if n is not s.root: s.cur=n.parent
    def handle_data(s,d): s.cur.children.append(d)
def parse(txt): b=B(); b.feed(txt); return b.root
