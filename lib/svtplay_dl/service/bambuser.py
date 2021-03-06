# ex:ts=4:sw=4:sts=4:et
# -*- tab-width: 4; c-basic-offset: 4; indent-tabs-mode: nil -*-
from __future__ import absolute_import
import re
import json
import copy

from svtplay_dl.service import Service, OpenGraphThumbMixin
from svtplay_dl.utils import get_http_data
from svtplay_dl.log import log
from svtplay_dl.fetcher.rtmp import RTMP
from svtplay_dl.fetcher.http import HTTP

class Bambuser(Service, OpenGraphThumbMixin):
    supported_domains = ["bambuser.com"]

    def get(self, options):
        match = re.search(r"v/(\d+)", self.url)
        if not match:
            log.error("Can't find video id in url")
            return

        if self.exclude(options):
            return

        json_url = "http://player-c.api.bambuser.com/getVideo.json?api_key=005f64509e19a868399060af746a00aa&vid=%s" % match.group(1)
        error, data = get_http_data(json_url)
        if error:
            log.error("Can't download video info")
            return

        info = json.loads(data)["result"]
        video = info["url"]
        if video[:4] == "rtmp":
            playpath = info["id"][len(info["id"])-36:]
            options.other = "-y %s" % playpath
            if info["type"] == "live":
                options.live = True
            yield RTMP(copy.copy(options), video, "0")
        else:
            yield HTTP(copy.copy(options), video, "0")

