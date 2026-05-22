def format_as_monospace_table(headers: list[str], rows: list[list[str]]) -> str:
    """
    Formats a list of headers and rows of strings into a clean, space-padded,
    monospaced table wrapped in a Markdown code block.
    """
    if not rows:
        return ""
        
    # Calculate max width for each column
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            if idx < len(col_widths):
                col_widths[idx] = max(col_widths[idx], len(str(val)))
            
    # Build header row
    header_parts = []
    divider_parts = []
    for idx, h in enumerate(headers):
        header_parts.append(f"{h:<{col_widths[idx]}}")
        divider_parts.append("-" * col_widths[idx])
    
    table_lines = [
        " | ".join(header_parts),
        "-|-".join(divider_parts)
    ]
    
    # Build data rows
    for row in rows:
        row_parts = []
        for idx, val in enumerate(row):
            if idx < len(col_widths):
                row_parts.append(f"{str(val):<{col_widths[idx]}}")
        table_lines.append(" | ".join(row_parts))
        
    return "```\n" + "\n".join(table_lines) + "\n```"
