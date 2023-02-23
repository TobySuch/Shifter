from django import template

register = template.Library()


def pretty_file_size(value):
    """Converts a file size in bytes to a human readable format"""
    bytes = int(value)
    kilobytes = bytes // 1024
    megabytes = kilobytes // 1024
    gigabytes = megabytes // 1024
    terabytes = gigabytes // 1024
    if bytes < 1024:
        return f"{bytes}B"
    elif kilobytes < 1024:
        return f"{kilobytes}KB"
    elif megabytes < 1024:
        return f"{megabytes}MB"
    elif gigabytes < 1024:
        return f"{gigabytes}GB"
    else:
        return f"{terabytes}TB"


register.filter('pretty_file_size', pretty_file_size)
