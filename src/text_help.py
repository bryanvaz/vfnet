
def wrap_text(text, max_width, lead_padding = 0):
    """Wraps the given text to the specified maximum width"""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line + word) + 1 <= max_width:
            current_line += " " + word
        else:
            lines.append(current_line.strip())
            current_line = word
    if current_line:
        lines.append("{:>{}}{}".format("", lead_padding, current_line.strip()))
    return lines
