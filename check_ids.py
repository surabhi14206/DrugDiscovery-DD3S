
from html.parser import HTMLParser

class IDFinder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = {}
        self.line_map = {}

    def handle_starttag(self, tag, attrs):
        for attr, value in attrs:
            if attr == 'id':
                line, _ = self.getpos()
                if value in self.ids:
                    self.ids[value].append(line)
                else:
                    self.ids[value] = [line]

file_path = "c:/Users/yadav/OneDrive/Desktop/DD/templates/visualization/design.html"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

parser = IDFinder()
parser.feed(content)

found = False
for id_val, lines in parser.ids.items():
    if len(lines) > 1:
        print(f"Duplicate ID '{id_val}' found on lines: {lines}")
        found = True

if not found:
    print("No duplicate IDs found.")
