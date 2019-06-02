# P2000 ONTVANGEN OP RASPBERRY PI 2 MET RTL-SDR
# https://nl.oneguyoneblog.com/2016/08/09/p2000-ontvangen-decoderen-raspberry-pi/
#
# vergeet niet deze regel verderop aan te passen aan je eigen RTL-SDR ontvanger (-p en -g):
# multimon_ng = subprocess.Popen("rtl_fm -f 169.65M -M fm -s 22050 -p 43
# -g 30 | multimon-ng -a FLEX -t raw -",


import time
import asyncio
import re
from datetime import datetime
import dateutil.parser


async def incidents_receiver(capcode_filter):
    with open("error.txt", "a") as file:
        curtime = time.strftime("%H:%M:%S %Y-%m-%d")
        file.write(("#" * 20) + "\n" + curtime + "\n")

    proc = await asyncio.create_subprocess_shell("rtl_fm -f 169.65M -M fm -s 22050 -p 43 -g 30 | multimon-ng -a FLEX -t raw -",
                            stdout=asyncio.subprocess.PIPE,
                            stderr=open("error.txt", "a"))

    while True:
        raw_data = await proc.stdout.readline()
        alert = parse_line_receiver(raw_data.decode("ascii"), capcode_filter)
        if alert:
            yield alert


def parse_line_receiver(line, capcode_filter):
    if not line:
        return None

    if "ALN" not in line:
        return None

    if not line.startswith("FLEX"):
        return

    flex = line[0:5]
    timestamp = dateutil.parser.parse(line[6:25])
    #group_id = line[35:41]
    capcode = line[45:54]
    message = line[60:].replace("\n", "")

    if capcode not in capcode_filter:
        return None

    regex_prio1 = "^A\s?1|\s?A\s?1|PRIO\s?1|^P\s?1"
    regex_prio2 = "^A\s?2|\s?A\s?2|PRIO\s?2|^P\s?2"
    regex_prio3 = "^B\s?1|^B\s?2|^B\s?3|PRIO\s?3|^P\s?3|PRIO\s?4|^P\s?4"

    priority = 0
    if re.search(regex_prio1, message, re.IGNORECASE):
        priority = 1
    elif re.search(regex_prio2, message, re.IGNORECASE):
        priority = 2
    elif re.search(regex_prio3, message, re.IGNORECASE):
        priority = 3

    return {
        "timestamp": timestamp,
        "priority": priority,
        "message": message,
    }