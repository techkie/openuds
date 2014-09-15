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
from __future__ import unicode_literals

from django.conf import settings
from uds.models import Config as dbConfig
from uds.core.managers.CryptoManager import CryptoManager
import logging

logger = logging.getLogger(__name__)

GLOBAL_SECTION = 'UDS'
SECURITY_SECTION = 'Security'
CLUSTER_SECTION = 'Cluster'

class Config(object):
    '''
    Keeps persistence configuration data
    '''

    # Fields types, so inputs get more "beautiful"
    TEXT_FIELD = 0
    LONGTEXT_FIELD = 1
    NUMERIC_FIELD = 2
    BOOLEAN_FIELD = 3

    class _Value(object):
        def __init__(self, section, key, default='', crypt=False, longText=False, **kwargs):
            self._type = kwargs.get('type', -1)
            self._section = section
            self._key = key
            self._crypt = crypt
            self._longText = longText
            if crypt is False:
                self._default = default
            else:
                self._default = CryptoManager.manager().encrypt(default)
            self._data = None

        def get(self, force=False):
            try:
                if force or self._data is None:
                    # logger.debug('Accessing db config {0}.{1}'.format(self._section.name(), self._key))
                    readed = dbConfig.objects.filter(section=self._section.name(), key=self._key)[0]
                    self._data = readed.value
                    self._crypt = [self._crypt, True][readed.crypt]  # True has "higher" precedende than False
                    self._longText = readed.long
                    if readed.field_type == -1 and self._type != -1:
                        readed.field_type = self._type
                        readed.save()
                    self._type = readed.field_type
            except Exception:
                # Not found
                if self._default != '' and self._crypt:
                    self.set(CryptoManager.manager().decrypt(self._default))
                elif not self._crypt:
                    self.set(self._default)
                self._data = self._default
            if self._crypt is True:
                return CryptoManager.manager().decrypt(self._data)
            else:
                return self._data

        def getInt(self, force=False):
            try:
                return int(self.get(force))
            except Exception:
                logger.error('Value for {0}.{1} is invalid (integer expected)'.format(self._section, self._key))
                try:
                    return int(self._default)
                except:
                    logger.error('Default value for {0}.{1} is also invalid (integer expected)'.format(self._section, self._key))
                    return -1

        def getBool(self, force=False):
            if self.get(force) == '0':
                return False
            return True

        def key(self):
            return self._key

        def section(self):
            return self._section.name()

        def isCrypted(self):
            return self._crypt

        def isLongText(self):
            return self._longText

        def getType(self):
            return self._type

        def set(self, value):
            if self._crypt is True:
                value = CryptoManager.manager().encrypt(value)
            '''
            Editable here means that this configuration value can be edited by admin directly (generally, that this is a "clean text" value)
            '''
            logger.debug('Saving config {0}.{1} as {2}'.format(self._section.name(), self._key, value))
            try:
                if dbConfig.objects.filter(section=self._section.name(), key=self._key).update(value=value, crypt=self._crypt, long=self._longText, field_type=self._type) == 0:
                    raise Exception()  # Do not exists, create a new one
            except Exception:
                try:
                    dbConfig.objects.create(section=self._section.name(), key=self._key, value=value, crypt=self._crypt, long=self._longText, field_type=self._type)
                except Exception:
                    # Probably a migration issue, just ignore it
                    logger.info("Could not save configuration key {0}.{1}".format(self._section.name(), self._key))

    class _Section:
        def __init__(self, sectionName):
            self._sectionName = sectionName

        def value(self, key, default='', **kwargs):
            return Config._Value(self, key, default, **kwargs)

        def valueCrypt(self, key, default='', **kwargs):
            return Config._Value(self, key, default, True, **kwargs)

        def valueLong(self, key, default='', **kwargs):
            return Config._Value(self, key, default, False, True, **kwargs)

        def name(self):
            return self._sectionName

    @staticmethod
    def section(sectionName):
        return Config._Section(sectionName)

    @staticmethod
    def enumerate():
        for cfg in dbConfig.objects.all().order_by('key'):
            logger.debug('{0}.{1}:{2},{3}'.format(cfg.section, cfg.key, cfg.value, cfg.field_type))
            if cfg.crypt is True:
                val = Config.section(cfg.section).valueCrypt(cfg.key)
            else:
                val = Config.section(cfg.section).value(cfg.key)
            yield val

    @staticmethod
    def update(section, key, value):
        # If cfg value does not exists, simply ignore request
        try:
            cfg = dbConfig.objects.filter(section=section, key=key)[0]
            if cfg.crypt is True:
                value = CryptoManager.manager().encrypt(value)
            cfg.value = value
            cfg.save()
            logger.debug('Updated value for {0}.{1} to {2}'.format(section, key, value))
        except Exception:
            pass


class GlobalConfig(object):
    '''
    Simple helper to keep track of global configuration
    '''
    SESSION_EXPIRE_TIME = Config.section(GLOBAL_SECTION).value('sessionExpireTime', '24', type=Config.NUMERIC_FIELD)  # Max session duration (in use) after a new publishment has been made
    # Delay between cache checks. reducing this number will increase cache generation speed but also will load service providers
    CACHE_CHECK_DELAY = Config.section(GLOBAL_SECTION).value('cacheCheckDelay', '19', type=Config.NUMERIC_FIELD)
    # Delayed task number of threads PER SERVER, with higher number of threads, deplayed task will complete sooner, but it will give more load to overall system
    DELAYED_TASKS_THREADS = Config.section(GLOBAL_SECTION).value('delayedTasksThreads', '4', type=Config.NUMERIC_FIELD)
    # Number of scheduler threads running PER SERVER, with higher number of threads, deplayed task will complete sooner, but it will give more load to overall system
    SCHEDULER_THREADS = Config.section(GLOBAL_SECTION).value('schedulerThreads', '3', type=Config.NUMERIC_FIELD)
    # Waiting time before removing "errored" and "removed" publications, cache, and user assigned machines. Time is in seconds
    CLEANUP_CHECK = Config.section(GLOBAL_SECTION).value('cleanupCheck', '3607', type=Config.NUMERIC_FIELD)
    # Time to maintaing "info state" items before removing it, in seconds
    KEEP_INFO_TIME = Config.section(GLOBAL_SECTION).value('keepInfoTime', '14401', type=Config.NUMERIC_FIELD)  # Defaults to 2 days 172800?? better 4 hours xd
    # Max number of services to be "preparing" at same time
    MAX_PREPARING_SERVICES = Config.section(GLOBAL_SECTION).value('maxPreparingServices', '15', type=Config.NUMERIC_FIELD)  # Defaults to 15 services at once (per service provider)
    # Max number of service to be at "removal" state at same time
    MAX_REMOVING_SERVICES = Config.section(GLOBAL_SECTION).value('maxRemovingServices', '15', type=Config.NUMERIC_FIELD)  # Defaults to 15 services at once (per service provider)
    # If we ignore limits (max....)
    IGNORE_LIMITS = Config.section(GLOBAL_SECTION).value('ignoreLimits', '0', type=Config.BOOLEAN_FIELD)
    # Number of services to initiate removal per run of CacheCleaner
    USER_SERVICE_CLEAN_NUMBER = Config.section(GLOBAL_SECTION).value('userServiceCleanNumber', '3', type=Config.NUMERIC_FIELD)  # Defaults to 3 per wun
    # Removal Check time for cache, publications and deployed services
    REMOVAL_CHECK = Config.section(GLOBAL_SECTION).value('removalCheck', '31', type=Config.NUMERIC_FIELD)  # Defaults to 30 seconds
    # Login URL
    LOGIN_URL = Config.section(GLOBAL_SECTION).value('loginUrl', '/login', type=Config.TEXT_FIELD)  # Defaults to /login
    # Session duration
    USER_SESSION_LENGTH = Config.section(SECURITY_SECTION).value('userSessionLength', '14400', type=Config.NUMERIC_FIELD)  # Defaults to 4 hours
    # Superuser (do not need to be at database!!!)
    SUPER_USER_LOGIN = Config.section(SECURITY_SECTION).value('superUser', 'root', type=Config.TEXT_FIELD)
    # Superuser password (do not need to be at database!!!)
    SUPER_USER_PASS = Config.section(SECURITY_SECTION).valueCrypt('rootPass', 'udsmam0', type=Config.TEXT_FIELD)
    # Idle time before closing session on admin
    SUPER_USER_ALLOW_WEBACCESS = Config.section(SECURITY_SECTION).value('allowRootWebAccess', '1', type=Config.BOOLEAN_FIELD)
    # Time an admi session can be idle before being "logged out"
    ADMIN_IDLE_TIME = Config.section(SECURITY_SECTION).value('adminIdleTime', '14400', type=Config.NUMERIC_FIELD)  # Defaults to 4 hous
    # Time betwen checks of unused services by os managers
    # Unused services will be invoked for every machine assigned but not in use AND that has been assigned at least this time
    # (only if os manager asks for this characteristic)
    CHECK_UNUSED_TIME = Config.section(GLOBAL_SECTION).value('checkUnusedTime', '631', type=Config.TEXT_FIELD)  # Defaults to 10 minutes
    # Default CSS Used
    CSS = Config.section(GLOBAL_SECTION).value('css', settings.STATIC_URL + 'css/uds.css', type=Config.TEXT_FIELD)
    # Max logins before blocking an account
    MAX_LOGIN_TRIES = Config.section(GLOBAL_SECTION).value('maxLoginTries', '3', type=Config.NUMERIC_FIELD)
    # Block time in second for an user that makes too many mistakes, 5 minutes default
    LOGIN_BLOCK = Config.section(GLOBAL_SECTION).value('loginBlockTime', '300', type=Config.NUMERIC_FIELD)
    # Do autorun of service if just one service.
    # 0 = No autorun, 1 = Autorun at login
    # In a future, maybe necessary another value "2" that means that autorun always
    AUTORUN_SERVICE = Config.section(GLOBAL_SECTION).value('autorunService', '0', type=Config.BOOLEAN_FIELD)
    # Redirect HTTP to HTTPS
    REDIRECT_TO_HTTPS = Config.section(GLOBAL_SECTION).value('redirectToHttps', '0', type=Config.BOOLEAN_FIELD)
    # Max time needed to get a service "fully functional" before it's considered "failed" and removed
    # The time is in seconds
    MAX_INITIALIZING_TIME = Config.section(GLOBAL_SECTION).value('maxInitTime', '3601', type=Config.NUMERIC_FIELD)
    # Custom HTML for login page
    CUSTOM_HTML_LOGIN = Config.section(GLOBAL_SECTION).value('customHtmlLogin', '', type=Config.LONGTEXT_FIELD)
    # Maximum logs per user service
    MAX_LOGS_PER_ELEMENT = Config.section(GLOBAL_SECTION).value('maxLogPerElement', '100', type=Config.NUMERIC_FIELD)
    # Time to restrain a deployed service in case it gives some errors at some point
    RESTRAINT_TIME = Config.section(GLOBAL_SECTION).value('restrainTime', '600', type=Config.NUMERIC_FIELD)
    # Number of errors that must occurr in RESTRAIN_TIME to restrain deployed service
    RESTRAINT_COUNT = Config.section(GLOBAL_SECTION).value('restrainCount', '3', type=Config.NUMERIC_FIELD)

    # Statistics duration, in days
    STATS_DURATION = Config.section(GLOBAL_SECTION).value('statsDuration', '365', type=Config.NUMERIC_FIELD)
    # If disallow login using /login url, and must go to an authenticator
    DISALLOW_GLOBAL_LOGIN = Config.section(GLOBAL_SECTION).value('disallowGlobalLogin', '0', type=Config.BOOLEAN_FIELD)

    # Allos preferences access to users
    PREFERENCES_ALLOWED = Config.section(GLOBAL_SECTION).value('allowPreferencesAccess', '1', type=Config.BOOLEAN_FIELD)

    # Allowed "trusted sources" for request
    TRUSTED_SOURCES = Config.section(SECURITY_SECTION).value('Trusted Hosts', '*', type=Config.TEXT_FIELD)

    # Clusters related vars

    # Maximum desired CPU Load. If cpu is over this value, a migration of a service is "desirable"
    CLUSTER_MIGRATE_CPULOAD = Config.section(CLUSTER_SECTION).value('Migration CPU Load', '80', type=Config.NUMERIC_FIELD)
    # Maximum CPU Load for a node to be elegible for destination of a migration
    CLUSTER_ELEGIBLE_CPULOAD = Config.section(CLUSTER_SECTION).value('Destination CPU Load', '60', type=Config.NUMERIC_FIELD)
    # Minimum desired Memory free for a cluster node. If free memory (in %) is under this percentage,
    # a migration of a service inside this node is "desirable"
    CLUSTER_MIGRATE_MEMORYLOAD = Config.section(CLUSTER_SECTION).value('Migration Free Memory', '20', type=Config.NUMERIC_FIELD)
    # Minimum Free memory for a node to be elegible for a destination of a migration
    CLUSTER_ELEGIBLE_MEMORYLOAD = Config.section(CLUSTER_SECTION).value('Migration Free Memory', '40', type=Config.NUMERIC_FIELD)

    # Gui vars
    UDS_THEME = Config.section(GLOBAL_SECTION).value('UDS Theme', 'html5', type=Config.TEXT_FIELD)

    # This is used so templates can change "styles" from admin interface
    UDS_THEME_VISUAL = Config.section(GLOBAL_SECTION).value('UDS Theme Enhaced', '1', type=Config.BOOLEAN_FIELD)

    initDone = False

    @staticmethod
    def initialize():
        try:
            if GlobalConfig.initDone is False:
                # All configurations are upper case
                # Tries to initialize database data for global config so it is stored asap and get cached for use
                for v in GlobalConfig.__dict__.itervalues():
                    if type(v) is Config._Value:
                        v.get()
            GlobalConfig.initDone = True
        except:
            logger.debug('Config table do not exists!!!, maybe we are installing? :-)')


# Context processor
def context_processor(request):
    return {'css_path': GlobalConfig.CSS.get()}

# Initialization of global configurations
GlobalConfig.initialize()