"""
Test Markdown rendering for AI chat responses
"""
import markdown
import bleach

# Test Markdown text similar to what Ollama might return
test_markdown = """**Chemical Properties:**

* **Boiling point:** 100°C
* **Molecular weight:** 18.015 g/mol
* **State:** Liquid at room temperature

The compound shows excellent *solubility* in **polar solvents**.

### Key Features:
1. High polarity
2. Strong hydrogen bonding
3. Universal solvent

```python
# Example calculation
mw = 18.015
density = 1.0
```

> Important: Always handle with proper safety equipment.
"""

# Convert Markdown to HTML
html_content = markdown.markdown(
    test_markdown,
    extensions=['extra', 'fenced_code', 'tables', 'nl2br']
)

# Sanitize HTML
safe_html = bleach.clean(
    html_content,
    tags=['p', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'br', 'code', 'pre', 
          'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'hr', 'table', 
          'thead', 'tbody', 'tr', 'th', 'td', 'a', 'span', 'div'],
    attributes={'a': ['href', 'title'], 'code': ['class'], 'span': ['class']},
    strip=True
)

print("Original Markdown:")
print("=" * 60)
print(test_markdown)
print("\n" + "=" * 60)
print("\nConverted to Safe HTML:")
print("=" * 60)
print(safe_html)
print("\n" + "=" * 60)
print("\n✅ Markdown conversion test complete!")
print("\nThis HTML will be rendered in the chat with proper formatting:")
print("- Bold text will appear bold")
print("- Italic text will appear italic")
print("- Lists will appear as bullet points")
print("- Code blocks will be highlighted")
print("- Blockquotes will have a colored border")
