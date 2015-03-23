# -*- coding: utf-8 -*-

#
# Copyright (c) 2012 Virtual Cable S.L.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#    * Neither the name of Virtual Cable S.L. nor the names of its contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''
@author: Adolfo Gómez, dkmaster at dkmon dot com
'''

from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from uds.core.util import OsDetector
import logging
import os
import sys

logger = logging.getLogger(__name__)


def scramble(data):
    '''
    Simple scrambler so password are not seen at source page
    '''
    res = []
    n = 0x32
    for c in data[::-1]:
        res.append(chr(ord(c) ^ n))
        n = (n + ord(c)) & 0xFF
    return "".join(res).encode('hex')


def generateHtmlForRdp(transport, idUserService, idTransport, os, ip, port, user, password, domain, extra):
    isMac = os['OS'] == OsDetector.Macintosh
    applet = reverse('uds.web.views.transcomp', kwargs={'idTransport': idTransport, 'componentId': '1'})
    logger.debug('Applet: {0}'.format(applet))
    # Gets the codebase, simply remove last char from applet
    codebase = applet[:-1]
    # We generate the "data" parameter
    data = [
        'u:' + user,
        'p:' + password,
        'd:' + domain,
        's:' + ip,
        'po:' + port,
        'sc:' + (extra['smartcards'] and '1' or '0'),
        'pr:' + (extra['printers'] and '1' or '0'),
        'se:' + (extra['serials'] and '1' or '0'),
        'dr:' + (extra['drives'] and '1' or '0'),
        'au:' + '1',  # Audio, 0 do not play, 1 play
        'w:' + str(extra['width']),
        'h:' + str(extra['height']),
        'c:' + str(extra['depth']),
        'cr:' + (extra['compression'] and '1' or '0'),
        'is:' + idUserService,
        'sw:' + (extra['wallpaper'] and '1' or '0'),
        'mm:' + (extra['multimon'] and '1' or '0'),
    ]

    logger.debug('Data: {0}'.format(data))

    if 'tun' in extra:
        data.append('tun:' + extra['tun'])

    data = scramble('\t'.join(data))
    res = '<div id="applet"><applet code="RdpApplet.class" codebase="%s" archive="%s" width="200" height="22"><param name="data" value="%s"/><param name="permissions" value="all-permissions"/></applet></div>' % (codebase, '1', data)
    if isMac is True:
        res += ('<div><p>' + _('In order to use this service, you should first install CoRD.') + '</p>'
                '<p><a href="/static/other/CoRD.pkg">' + _('Download CoRD') + '</a></p>'
                '</div>'
                '<div>'
                '<p>' + _('Attention Safari Users:') + '<br/>'
                '<p>' + _('In order to access theese services, you will need to enable this in order to access to service:') + '</p>'
                '<p>' + _('Go to Safari > Preferences > Security > Manage Website Settings') + '</p>'
                '<p>' + _('Click Java in left hand panel, and select site to allow UDS Rdp, and set it to Allow Always (also mark "Unsecure mode").') + '</p>'
                '<p>' + _('Users of Firefox or Chrome:') + '</p>'
                '<p>' + _('If any warning is shown when launching RDP Applet, press "ignore" and continue') + '</p>'
                '</div>'
                )
    return res


def getHtmlComponent(module, componentId):
    filesDict = {
        '1': ['rdp.jar', 'application/java-archive'],
        '2': ['rdppass.dll', 'application/x-msdos-program'],
        '3': ['launcher.jar', 'application/java-archive']
    }

    if componentId not in filesDict:
        return ['text/plain', 'no component']
    fname = os.path.dirname(sys.modules[module].__file__) + '/applet/' + filesDict[componentId][0]
    logger.debug('Loading component {0} from {1}'.format(componentId, fname))

    with open(fname, 'rb') as f:
        data = f.read()

    return [filesDict[componentId][1], data]
