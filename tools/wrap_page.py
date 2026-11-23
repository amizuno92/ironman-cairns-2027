"""Wrap a page fragment (boards/*.html) in the full document skeleton the artifact server needs.

Usage: python tools/wrap_page.py boards/week7.html out.html [state.json]
If state.json is given, it replaces the board's embedded state (keeps Andrew's moves/ticks).
"""
import re
import sys

RESET = (":root{color-scheme:light;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);"
         "padding-bottom:env(safe-area-inset-bottom,0px)}html{scroll-padding-top:env(safe-area-inset-top,0px)}"
         "body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#000}"
         "img{max-width:100%}[hidden]:not([hidden=until-found i]){display:none!important}")

src, out = sys.argv[1], sys.argv[2]
c = open(src).read()
if len(sys.argv) > 3:
    st = open(sys.argv[3]).read().strip()
    c, k = re.subn(r'(<script type="application/json" id="state">).*?(</script>)', lambda m: m.group(1) + st + m.group(2), c, count=1, flags=re.S)
    assert k == 1, "state block not found"
open(out, "w").write('<!DOCTYPE html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,'
                     'initial-scale=1,viewport-fit=cover"><style>' + RESET + '</style></head><body>' + c + '</body></html>')
