# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import sys
import time
import re
import os
import io
import platform
from datetime import timedelta

from svtplay_dl.utils import is_py3, is_py2, filenamify, decode_html_entities
from svtplay_dl.utils.terminal import get_terminal_size
from svtplay_dl.log import log

progress_stream = sys.stderr

class ETA(object):
    """
    An ETA class, used to calculate how long it takes to process
    an arbitrary set of items. By initiating the object with the
    number of items and continuously updating with current
    progress, the class can calculate an estimation of how long
    time remains.
    """

    def __init__(self, end, start=0):
        """
        Parameters:
        end:   the end (or size, of start is 0)
        start: the starting position, defaults to 0
        """
        self.start = start
        self.end = end
        self.pos = start

        self.now = time.time()
        self.start_time = self.now

    def update(self, pos):
        """
        Set new absolute progress position.

        Parameters:
        pos: new absolute progress
        """
        self.pos = pos
        self.now = time.time()

    def increment(self, skip=1):
        """
        Like update, but set new pos relative to old pos.

        Parameters:
        skip: progress since last update (defaults to 1)
        """
        self.update(self.pos + skip)

    @property
    def left(self):
        """
        returns: How many item remains?
        """
        return self.end - self.pos

    def __str__(self):
        """
        returns: a time string of the format HH:MM:SS.
        """
        duration = self.now - self.start_time

        # Calculate how long it takes to process one item
        try:
            elm_time = duration / (self.end - self.left)
        except ZeroDivisionError:
            return "(unknown)"

        return str(timedelta(seconds=int(elm_time * self.left)))


def progress(byte, total, extra=""):
    """ Print some info about how much we have downloaded """
    if total == 0:
        progresstr = "Downloaded %dkB bytes" % (byte >> 10)
        progress_stream.write(progresstr + '\r')
        return
    progressbar(total, byte, extra)

def progressbar(total, pos, msg=""):
    """
    Given a total and a progress position, output a progress bar
    to stderr. It is important to not output anything else while
    using this, as it relies soley on the behavior of carriage
    return (\\r).

    Can also take an optioal message to add after the
    progressbar. It must not contain newlines.

    The progress bar will look something like this:

    [099/500][=========...............................] ETA: 13:36:59

    Of course, the ETA part should be supplied be the calling
    function.
    """
    width = get_terminal_size()[0] - 35
    rel_pos = int(float(pos)/total*width)
    bar = ''.join(["=" * rel_pos, "." * (width - rel_pos)])

    # Determine how many digits in total (base 10)
    digits_total = len(str(total))
    fmt_width = "%0" + str(digits_total) + "d"
    fmt = "\r[" + fmt_width + "/" + fmt_width + "][%s] %s"

    progress_stream.write(fmt % (pos, total, bar, msg))

def filename(options, stream):
    if options.output:
        if is_py2:
            if platform.system() == "Windows":
                options.output = options.output.decode("latin1")
            else:
                options.output = options.output.decode("utf-8")
        options.output = options.output.replace('"', '').replace("'", "").rstrip('\\')
    if not options.output or os.path.isdir(options.output):
        error, data = stream.get_urldata()
        if error:
            log.error("Cant find that page")
            return False
        if data is None:
            return False
        match = re.search(r"(?i)<title[^>]*>\s*(.*?)\s*</title>", data, re.S)
        if match:
            options.output_auto = True
            title_tag = decode_html_entities(match.group(1))
            if not options.output:
                options.output = filenamify(title_tag)
            else:
                # output is a directory
                options.output = os.path.join(options.output, filenamify(title_tag))

    if platform.system() == "Windows":
        # ugly hack. replace \ with / or add extra \ because c:\test\kalle.flv will add c:_tab_est\kalle.flv
        if options.output and options.output.find("\\") > 0:
            options.output = options.output.replace("\\", "/")
    return True

def output(options, extention="mp4", openfd=True):
    if is_py3:
        file_d = io.IOBase
    else:
        file_d = file

    if options.output != "-":
        ext = re.search(r"(\.[a-z0-9]+)$", options.output)
        if not ext:
            options.output = "%s.%s" % (options.output, extention)
        if extention == "srt" and ext:
            options.output = "%s.srt" % options.output[:options.output.rfind(ext.group(1))]
        log.info("Outfile: %s", options.output)
        if os.path.isfile(options.output) or \
                findexpisode(os.path.dirname(os.path.realpath(options.output)), options.service, os.path.basename(options.output)):
            if extention == "srt":
                if not options.force_subtitle:
                    log.error("File already exists. Use --force-subtitle to overwrite")
                    return None
            else:
                if not options.force:
                    log.error("File already exists. Use --force to overwrite")
                    return None
        if openfd:
            file_d = open(options.output, "wb")
    else:
        if openfd:
            if is_py3:
                file_d = sys.stdout.buffer
            else:
                file_d = sys.stdout

    return file_d

def findexpisode(directory, service, name):
    match = re.search(r"-(\w+)-\w+.(\w{2,3})$", name)
    if not match:
        return False
    videoid = match.group(1)
    extention = match.group(2)
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    for i in files:
        match = re.search(r"-(\w+)-\w+.(\w{2,3})$", i)
        if match:
            if service:
                if extention == "srt":
                    if name.find(service) and match.group(1) == videoid and match.group(2) == extention:
                        return True
                elif match.group(2) != "srt":
                    if name.find(service) and match.group(1) == videoid:
                        return True

    return False
