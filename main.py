import tkinter as tk
from tkinter import simpledialog, scrolledtext
from bs4 import BeautifulSoup
import html

class HTMLToPythonConverter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("HTML to Python Converter")
        self.root.geometry("800x600")

        self.create_widgets()

    def create_widgets(self):
        input_frame = tk.Frame(self.root)
        input_frame.pack(fill=tk.BOTH, expand=True)

        input_label = tk.Label(input_frame, text="Enter HTML code:")
        input_label.pack()

        self.input_text = scrolledtext.ScrolledText(input_frame, height=10)
        self.input_text.pack(fill=tk.BOTH, expand=True)

        convert_button = tk.Button(self.root, text="Convert to Python", command=self.convert)
        convert_button.pack()

        output_frame = tk.Frame(self.root)
        output_frame.pack(fill=tk.BOTH, expand=True)

        output_label = tk.Label(output_frame, text="Python code:")
        output_label.pack()

        self.output_text = scrolledtext.ScrolledText(output_frame, height=10)
        self.output_text.pack(fill=tk.BOTH, expand=True)

    def convert(self):
        html_code = self.input_text.get("1.0", tk.END)
        python_code = self.html_to_python(html_code)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, python_code)

    def html_to_python(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        def process_element(element, indent=0):
            if element.name is None:
                text = element.strip()
                if text:
                    return f"{'    ' * indent}print(html.escape('{text}'))"
            else:
                lines = [f"{'    ' * indent}print('<{element.name}{self.get_attributes(element)}>')" if element.name not in ['script', 'style'] else '']
                
                if element.name == 'script':
                    lines.append(f"{'    ' * (indent+1)}print('''\\n{element.string.strip()}''')")
                elif element.name == 'style':
                    lines.append(f"{'    ' * (indent+1)}print('''\\n{element.string.strip()}''')")
                else:
                    for child in element.children:
                        result = process_element(child, indent + 1)
                        if result:
                            lines.append(result)
                
                if element.name not in ['script', 'style']:
                    lines.append(f"{'    ' * indent}print('</{element.name}>')")
                return '\n'.join(lines)

        python_code = "import html\n\ndef generate_html():\n"
        python_code += process_element(soup)
        python_code += "\n\ngenerate_html()"
        return python_code

    def get_attributes(self, tag):
        return ''.join(f' {key}="{value}"' for key, value in tag.attrs.items())

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = HTMLToPythonConverter()
    app.run()