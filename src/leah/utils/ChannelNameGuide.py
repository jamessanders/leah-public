def get_direct_channel_name(handle1, handle2):
    names = [handle1, handle2]
    names.sort()
    return "#" + names[0] + "->" + names[1]

def is_direct_channel(channel_name):
    return "->" in channel_name