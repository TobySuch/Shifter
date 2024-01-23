from django import template

register = template.Library()


def pretty_file_size(value):
    """Converts a file size in bytes to a human readable format"""
    bytes = int(value)
    kilobytes = bytes // 1000
    megabytes = kilobytes // 1000
    gigabytes = megabytes // 1000
    terabytes = gigabytes // 1000
    if bytes < 1000:
        return f"{bytes}B"
    elif kilobytes < 1000:
        return f"{kilobytes}KB"
    elif megabytes < 1000:
        return f"{megabytes}MB"
    elif gigabytes < 1000:
        return f"{gigabytes}GB"
    else:
        return f"{terabytes}TB"


register.filter("pretty_file_size", pretty_file_size)
